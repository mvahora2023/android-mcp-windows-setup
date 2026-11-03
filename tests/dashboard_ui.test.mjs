import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const html=fs.readFileSync(new URL('../dashboard/index.html', import.meta.url),'utf8');
const js=html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
const raw=js?.match(/const PROJECT = (\{[^\n]+\});\nconst \$=/)?.[1];
test('project dataset parses, is complete, and uses valid source URLs',()=>{
 assert.ok(js);assert.doesNotThrow(()=>new vm.Script(js));
 assert.ok(raw);const p=JSON.parse(raw);
 assert.ok(p.rows.length>0);assert.equal(p.metrics.length,4);
 assert.equal(new Set(p.rows.map(x=>x.id)).size,p.rows.length);
 for(const r of p.rows){
  assert.ok(r.title&&r.group&&r.state);
  assert.match(r.source,/^https:\/\/github\.com\/mvahora2023\//);
 }
});
test('dashboard is offline-ready and transparent',()=>{
 assert.match(html,/Source transparency/);
 assert.match(html,/static, locally runnable/i);
 assert.match(html,/Export filtered data/);
 assert.doesNotMatch(html,/<script[^>]+src=/i);
});
