'use strict';
function flyoutBounds(tray, area, requested={width:424,height:512}) {
  const margin=12;
  const width=Math.min(requested.width,area.width-margin*2);
  const height=Math.min(requested.height,area.height-margin*2);
  const clamp=(v,a,b)=>Math.max(a,Math.min(v,b));
  let x=tray.x+tray.width-width;
  let y=area.y+area.height-height-margin;
  if(tray.y+tray.height<=area.y+8)y=area.y+margin;
  if(tray.x+tray.width<=area.x+8)x=area.x+margin;
  return {x:Math.round(clamp(x,area.x+margin,area.x+area.width-width-margin)),
    y:Math.round(clamp(y,area.y+margin,area.y+area.height-height-margin)),width,height};
}
module.exports={flyoutBounds};
