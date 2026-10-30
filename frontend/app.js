const $ = id => document.getElementById(id);
let current = null;
const labels = {running:'正在生成',completed:'已完成',needs_input:'需要补充信息',failed:'执行失败',budget_exceeded:'达到执行上限'};
function element(tag, text, cls) { const node=document.createElement(tag); if(text!==undefined) node.textContent=text; if(cls) node.className=cls; return node; }
async function api(url, options) {
  const response=await fetch(url,options); const data=await response.json();
  if(!response.ok) throw new Error(data.error || '请求失败'); return data;
}
function selectTab(id) {
  document.querySelectorAll('[data-tab]').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.tab===id)));
  ['script','checks','trace'].forEach(tab=>$(tab).hidden=tab!==id);
}
document.querySelectorAll('[data-tab]').forEach(b=>b.addEventListener('click',()=>selectTab(b.dataset.tab)));
$('mode').addEventListener('change',()=>{
  const live=$('mode').value==='live'; $('scenario').disabled=live;
  $('mode-note').textContent=live?'使用后端 .env 配置的模型。需求与素材将发送到该服务，可能产生调用费用。':'固定策略与模板，不代表真实模型决策。';
});
function render(job) {
  current=job; const result=job.result;
  $('status').textContent=labels[job.status] || job.status;
  $('notice').textContent=job.error || result?.reason || '任务已结束';
  $('download').disabled=!job.markdown; $('download-json').disabled=false;
  for(const id of ['script','checks','trace']) $(id).replaceChildren();
  if(!result) { $('script').append(element('p',job.error || '没有生成结果','error')); return; }
  const draft=result.script, duration=result.duration;
  if(draft) {
    $('script').append(element('h2',draft.title));
    const metrics=element('div',undefined,'metrics');
    for(const [label,value] of [['总估算',duration?.total_seconds],['旁白',duration?.voice_seconds],['额外停留',duration?.padding_seconds]]) {
      const metric=element('div',undefined,'metric'); metric.append(element('b',value===undefined?'—':`${value}s`),element('span',label)); metrics.append(metric);
    }
    $('script').append(metrics);
    for(const scene of draft.scenes) {
      const card=element('article',undefined,'scene'), head=element('div',undefined,'scene-head');
      const seconds=duration?.scenes.find(s=>s.scene_id===scene.scene_id)?.seconds;
      head.append(element('span',scene.scene_id),element('span',seconds===undefined?'未估算':`${seconds} 秒`));
      card.append(head,element('p',`画面 · ${scene.visual}`),element('p',`旁白 · ${scene.voiceover || '无'}`),element('p',`字幕 · ${scene.subtitle || '无'}`),element('small',`引用 · ${scene.claims.map(c=>c.fact_id).join(' / ') || '中性过渡，无产品断言'}`));
      $('script').append(card);
    }
  } else $('script').append(element('p','本次没有生成草稿。请查看结束原因或执行记录。','hint'));
  const report=result.checks;
  $('checks').append(element('h2',report?.passed===true?'检查通过':report?.passed===false?'检查未通过':'尚未执行检查'));
  for(const issue of report?.issues || []) $('checks').append(element('p',`${issue.scene_id || '全局'} · ${issue.code}：${issue.suggestion || issue.field || issue.term || ''}`,'error'));
  for(const risk of result.risks || []) $('checks').append(element('p',risk,'hint'));
  $('checks').append(element('p',`实际引用来源：${result.sources.join('、') || '无'}`,'hint'));
  for(const event of job.trace || []) {
    const card=element('article',undefined,'event');
    card.append(element('strong',`${String(event.step).padStart(2,'0')} · ${event.action}`),element('p',event.reason || '输出结构校验或接口错误'),element('pre',JSON.stringify({参数:event.arguments || {},观察:event.observation},null,2)));
    $('trace').append(card);
  }
}
$('brief').addEventListener('submit',async event=>{
  event.preventDefault(); current=null; $('generate').disabled=true; $('download').disabled=true; $('download-json').disabled=true;
  $('status').textContent='正在生成'; $('notice').textContent='任务提交后将在后台执行；完成前请保持页面打开。';
  for(const tab of ['script','checks','trace']) $(tab).replaceChildren(element('p','新任务运行中，完成后展示结果。','hint'));
  try {
    const payload={mode:$('mode').value,max_steps:Number($('steps').value),request:{topic:$('topic').value,audience:$('audience').value,platform:$('platform').value,target_seconds:Number($('duration').value),style:$('style').value,product_id:$('product').value,query:$('query').value,demo_scenario:$('scenario').value}};
    const {id}=await api('/api/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    let job;
    do { await new Promise(resolve=>setTimeout(resolve,1200)); job=await api(`/api/jobs/${id}`); $('notice').textContent=`任务 ${id} · 后台执行中，正在等待模型与工具结果…`; } while(job.status==='running');
    render(job);
  } catch(error) { $('status').textContent='请求失败'; $('notice').textContent=error.message; }
  finally { $('generate').disabled=false; }
});
function download(text, name, type) {
  const url=URL.createObjectURL(new Blob([text],{type})); const link=element('a'); link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
$('download').addEventListener('click',()=>{if(current?.markdown) download(current.markdown,`${current.id}.md`,'text/markdown;charset=utf-8');});
$('download-json').addEventListener('click',()=>{if(current) download(JSON.stringify(current,null,2),`${current.id}.json`,'application/json');});
api('/api/materials').then(data=>{
  $('materials').replaceChildren(); for(const material of data.materials) {const row=element('div',undefined,'material');row.append(element('code',material.id),element('span',material.facts.map(f=>f.text).join('；')));$('materials').append(row);}
}).catch(error=>$('materials').textContent=error.message);
