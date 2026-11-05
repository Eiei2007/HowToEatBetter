"""Build Markdown chapters and the standalone page from data.json; no third-party dependencies."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import argparse, hashlib, json, re

def fingerprint(x,sources):
    fields=['title','chapter','action','cost','benefitDetail','remark','evidenceNote','sourceKeys','evidence','value','returns','money','time','effort','scene']
    def normalize(v):
        if isinstance(v,str): return re.sub(r'\s+','',v)
        if isinstance(v,list): return [normalize(t) for t in v]
        return v
    body={k:normalize(x.get(k)) for k in fields}
    body['sources']={k:{f:sources[k][f] for f in ['title','url','type','supports']} for k in x['sourceKeys']}
    return hashlib.sha256(json.dumps(body,ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def build(root):
    d=json.loads((root/'data.json').read_text())
    today=datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    ids=[x['id'] for x in d['items']]
    if len(ids)!=len(set(ids)): raise ValueError('Duplicate entry IDs')
    for x in d['items']:
        for k in ['title','action','cost','benefitDetail','remark','evidenceNote','sourceKeys','evidence','value','returns','money','time','effort','scene','chapter']:
            if not x.get(k): raise ValueError(f'Missing {k}: {x["id"]}')
        if x['evidence'] not in ['A','B','C']: raise ValueError('Invalid evidence rating')
        for k in x['sourceKeys']:
            if k not in d['sourceDetails']:raise ValueError(f'Unknown source {k}')
        fp=fingerprint(x,d['sourceDetails'])
        x.setdefault('createdAt',today);x.setdefault('updatedAt',None)
        x.setdefault('changes',[{'date':x['createdAt'],'type':'新增','summary':'首次发布。'}])
        if x.get('contentFingerprint') and x['contentFingerprint']!=fp:
            x['updatedAt']=today
            x['changes'].append({'date':today,'type':'修改','summary':x.pop('changeSummary','更新正文、评级或来源；详见 GitHub 提交差异。')})
        x['contentFingerprint']=fp
    (root/'data.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
    n=len(d['items']);nc=len(d['chapters']);ns=len(d['sourceDetails'])
    template=(root/'site/template.html').read_text()
    page=template.replace('__DATA__',json.dumps(d,ensure_ascii=False).replace('</','<\\/'))
    page=page.replace('__ENTRY_COUNT__',str(n)).replace('__CHAPTER_COUNT__',str(nc)).replace('__SOURCE_COUNT__',str(ns))
    (root/'index.html').write_text(page)
    book=root/'book';book.mkdir(exist_ok=True)
    for number,c in enumerate(d['chapters'],1):
        out=f'# {number}. {c["title"]}\n\n{c["description"]}\n\n'
        for x in [x for x in d['items'] if x['chapter']==c['title']]:
            tags=f"**性价比 {x['value']}** · **证据 {x['evidence']} 级** · 换回：{'、'.join(x['returns'])} · 花钱：{x['money']} · 时间：{x['time']} · 毅力：{x['effort']}"
            dt=x['updatedAt'] or x['createdAt'];tp='修改' if x['updatedAt'] else '新增'
            out+=f"## {x['id']:02d} · {x['title']}\n\n{tags} · **{dt} {tp}**\n\n{x['action']}\n\n### 成本\n\n{x['cost']}\n\n### 收益\n\n{x['benefitDetail']}\n\n### 备注\n\n{x['remark']}\n\n### 来源与证据范围\n\n**为什么是 {x['evidence']} 级：** {x['evidenceNote']}\n\n"
            for k in x['sourceKeys']:
                s=d['sourceDetails'][k]
                out+=f"- [{s['title']}]({s['url']})\n  - 类型：{s['type']}。支持：{s['supports']}。\n  - 核实：{s['status']}；查阅日期：{s['checkedAt']}。\n"
            out+='\n<details><summary>修改记录</summary>\n\n'+''.join(f"- {h['date']} · {h['type']}：{h['summary']}\n" for h in reversed(x['changes']))+'\n</details>\n\n'
        (book/f'{number:02d}.md').write_text(out)
    readme=f'''# 高性价比饮食指南

从中国人的厨房、食堂和外卖出发，具体回答：怎么吃、花什么成本、能换回什么、证据支持到哪里。

**[在线阅读与筛选](https://eiei2007.github.io/HowToEatBetter/)**

当前有 **{nc} 章、{n} 条建议、{ns} 个来源**。每条包含展开说明、成本、收益、备注、研究类型与核实状态。阅读顺序不等于性价比排序，可按标签挑选。

## 六组标签

| 标签 | 选项与口径 |
| --- | --- |
| 性价比 | 极高 / 高 / 一般；编辑判断，同类目标内比较 |
| 证据等级 | A 绿色：试验；B 黄色：观察研究；C 灰色：指南、操作或执行建议 |
| 换回什么 | 寿命 / 健康 / 钱 / 时间精力；不同口径不互相换算 |
| 花钱 | 不花钱 / 少 / 多；额外购买为主，具体条件写在成本里 |
| 花时间 | 顺手 / 几分钟 / 每天占用；额外操作的估计 |
| 要毅力 | 不用 / 一点 / 很多；因个人习惯和环境而异 |

A/B/C 是研究设计的简化索引，**不是正式 GRADE 质量评价**。A 级也可能样本小、随访短或结果不确定。若研究只支持血压、体重改善，不自动标“换寿命”；若操作本身只有实践依据，不能直接继承相关原则的 A 级。

每条标签后显示真实的“某月某日新增／改过”，点日期可看修改记录。排版调整不更新条目日期。

## 目录

'''
    readme+=''.join(f'{i}. [{c["title"]}](book/{i:02d}.md)\n' for i,c in enumerate(d['chapters'],1))
    readme+='''
## 研究与维护

- [来源核实记录](docs/SOURCES.md)：逐个来源说明研究类型、支持范围与可访问程度。
- [评级口径](docs/RATINGS.md)：为什么不是所有建议都应该标 A。
- [更新记录](docs/CHANGELOG.md)：内容版本与逐条日期。
- [如何修改内容](CONTRIBUTING.md)：只改 data.json，再运行生成脚本，同步网页与章节。
- [发布说明](docs/PUBLISH.md)：GitHub Pages 从 main 根目录发布。

面向一般健康成年人；特殊疾病、孕期、儿童及其他营养需求请结合针对性指导。这里不替代诊疗，也不承诺个体延寿或减重结果。检索是有范围的资料整理，不声称穷尽全球文献或完成独立系统综述。

版式与信息结构参考 [HowToLiveBetter](https://eternity4719.github.io/HowToLiveBetter/)（原项目标注 CC BY 4.0），正文与代码重新编写。当前项目许可证仍待仓库所有者选择。
'''
    (root/'README.md').write_text(readme)
    source_md='# 来源与核实记录\n\n本版按主题检索国内外原始研究、系统综述与官方指南，主要使用期刊网站、PubMed、Cochrane 和卫生/食品安全部门。检索日期：2026-11-05。不是穷尽文献的系统综述，也未完成双人筛选、偏倚评估或正式 GRADE 分级。\n\n检索重点：糖与体重、钠与血压及卒中、全谷/蔬果/坚果/肉蛋与长期风险、减重方案、特殊饮食、家庭食品安全。优先记录直接结局，不把替代指标自动换成死亡收益。机构新闻稿用于解释同一研究，不计作额外独立试验。\n\n'
    for k,s in d['sourceDetails'].items():
        used=', '.join(str(x['id']) for x in d['items'] if k in x['sourceKeys'])
        source_md+=f"## {k} · {s['title']}\n\n[原始链接]({s['url']})\n\n- 类型：{s['type']}\n- 支持范围：{s['supports']}\n- 核实状态：{s['status']}\n- 查阅日期：{s['checkedAt']}\n- 用于条目：{used}\n\n"
    (root/'docs/SOURCES.md').write_text(source_md)
    ch='# 更新记录\n\n## 2026-11-05 · 详细扩充版\n\n从 22 条扩充到 44 条，重写原有条目，加入研究范围、核实状态、条目日期与自动同步工具。保留既有条目 ID，网页锚点仍使用 e-ID。\n\n日期表示站内实质内容变更，不等于论文发表日期，也不表示当天新增的研究。既有 22 条为改写，后续 22 条为新增，均如实标记本次日期。\n\n## 逐条记录\n\n'
    ch+=''.join(f"- [{x['id']:02d} {x['title']}](https://eiei2007.github.io/HowToEatBetter/#e-{x['id']})：{x['updatedAt'] or x['createdAt']} {'修改' if x['updatedAt'] else '新增'}\n" for x in d['items'])
    (root/'docs/CHANGELOG.md').write_text(ch)
    print(f'Built {n} entries, {nc} chapters, {ns} sources')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);args=parser.parse_args();build(args.root)
