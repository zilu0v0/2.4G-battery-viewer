const {test}=require('node:test');
const assert=require('node:assert/strict');
const {flyoutBounds}=require('../geometry');
test('bottom tray stays inside usable desktop',()=>{
  const b=flyoutBounds({x:1800,y:1040,width:24,height:24},{x:0,y:0,width:1920,height:1040});
  assert.equal(b.y,516);assert.equal(b.x,1400);assert.equal(b.height,512);
});
test('negative-coordinate secondary display',()=>{
  const a={x:-1920,y:-200,width:1920,height:1040};
  const b=flyoutBounds({x:-120,y:840,width:24,height:24},a);
  assert(b.x>=a.x&&b.x+b.width<=0);assert(b.y>=a.y&&b.y+b.height<=840);
});
test('top and left taskbars',()=>{
  const a={x:60,y:48,width:1860,height:1032};
  const top=flyoutBounds({x:1600,y:0,width:24,height:24},a);
  assert.equal(top.y,60);
  const left=flyoutBounds({x:0,y:900,width:24,height:24},a);assert.equal(left.x,72);
});
test('small work area clamps size and position',()=>{
  const b=flyoutBounds({x:390,y:450,width:24,height:24},{x:0,y:0,width:400,height:450});
  assert.deepEqual(b,{x:12,y:12,width:376,height:426});
});
