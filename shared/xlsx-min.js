/* Export .xlsx minimal, sans dépendance : un classeur, une feuille, chaînes en ligne, nombres typés.
   Le fichier est un zip « stored » (sans compression) écrit à la main : Excel, Numbers et LibreOffice l'ouvrent.
   Usage : ACBB_XLSX.telecharger('fichier.xlsx', 'Feuille', [['En-tête', …], [valeur, …], …]).
   Utilisable dans le navigateur et dans les tests Node (module.exports). */
(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports) module.exports=api;
  else root.ACBB_XLSX=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const CRC=(()=>{ const t=new Uint32Array(256); for(let n=0;n<256;n++){ let c=n; for(let k=0;k<8;k++) c=c&1?0xEDB88320^(c>>>1):c>>>1; t[n]=c>>>0; } return t; })();
  function crc32(u8){ let c=0xFFFFFFFF; for(let i=0;i<u8.length;i++) c=CRC[(c^u8[i])&0xFF]^(c>>>8); return (c^0xFFFFFFFF)>>>0; }
  const enc=s=>new TextEncoder().encode(s);
  const esc=s=>String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  function colName(i){ let s=''; i++; while(i>0){ const m=(i-1)%26; s=String.fromCharCode(65+m)+s; i=Math.floor((i-1)/26); } return s; }
  /* Feuille : la première ligne est l'en-tête (gras), les nombres restent des nombres, le reste du texte. */
  function sheetXml(rows,widths){
    const cols=widths&&widths.length?'<cols>'+widths.map((w,i)=>'<col min="'+(i+1)+'" max="'+(i+1)+'" width="'+w+'" customWidth="1"/>').join('')+'</cols>':'';
    const body=rows.map((r,ri)=>'<row r="'+(ri+1)+'">'+r.map((v,ci)=>{
      const ref=colName(ci)+(ri+1);
      if(v==null||v==='') return '';
      if(typeof v==='number'&&Number.isFinite(v)) return '<c r="'+ref+'"'+(ri===0?' s="1"':'')+'><v>'+v+'</v></c>';
      return '<c r="'+ref+'" t="inlineStr"'+(ri===0?' s="1"':'')+'><is><t xml:space="preserve">'+esc(v)+'</t></is></c>';
    }).join('')+'</row>').join('');
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'+cols+'<sheetData>'+body+'</sheetData>'+(rows.length>1?'<autoFilter ref="A1:'+colName(rows[0].length-1)+rows.length+'"/>':'')+'</worksheet>';
  }
  function classeur(nomFeuille,rows,widths){
    const feuille=esc(nomFeuille||'Feuille1').slice(0,31);
    return [
      ['[Content_Types].xml','<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>'],
      ['_rels/.rels','<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'],
      ['xl/workbook.xml','<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="'+feuille+'" sheetId="1" r:id="rId1"/></sheets></workbook>'],
      ['xl/_rels/workbook.xml.rels','<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'],
      ['xl/styles.xml','<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border/></borders><cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" applyFont="1"/></cellXfs></styleSheet>'],
      ['xl/worksheets/sheet1.xml',sheetXml(rows,widths)]
    ];
  }
  /* Zip « stored » : en-tête local + données par fichier, puis répertoire central et fin de répertoire. */
  function zip(entries){
    const parts=[], central=[]; let offset=0;
    const d=new Date(), dosTime=(d.getHours()<<11)|(d.getMinutes()<<5)|(d.getSeconds()>>1), dosDate=((d.getFullYear()-1980)<<9)|((d.getMonth()+1)<<5)|d.getDate();
    const u16=n=>[n&255,(n>>>8)&255], u32=n=>[n&255,(n>>>8)&255,(n>>>16)&255,(n>>>24)&255];
    entries.forEach(([name,text])=>{
      const nameB=enc(name), data=enc(text), crc=crc32(data);
      const head=new Uint8Array([80,75,3,4,...u16(20),...u16(0x0800),...u16(0),...u16(dosTime),...u16(dosDate),...u32(crc),...u32(data.length),...u32(data.length),...u16(nameB.length),...u16(0),...nameB]);
      parts.push(head,data);
      central.push(new Uint8Array([80,75,1,2,...u16(20),...u16(20),...u16(0x0800),...u16(0),...u16(dosTime),...u16(dosDate),...u32(crc),...u32(data.length),...u32(data.length),...u16(nameB.length),...u16(0),...u16(0),...u16(0),...u16(0),...u32(0),...u32(offset),...nameB]));
      offset+=head.length+data.length;
    });
    const cdSize=central.reduce((s,c)=>s+c.length,0);
    const end=new Uint8Array([80,75,5,6,...u16(0),...u16(0),...u16(entries.length),...u16(entries.length),...u32(cdSize),...u32(offset),...u16(0)]);
    const all=[...parts,...central,end], out=new Uint8Array(all.reduce((s,a)=>s+a.length,0)); let p=0;
    all.forEach(a=>{ out.set(a,p); p+=a.length; });
    return out;
  }
  function octets(nomFeuille,rows,widths){ return zip(classeur(nomFeuille,rows,widths)); }
  function telecharger(nomFichier,nomFeuille,rows,widths){
    const blob=new Blob([octets(nomFeuille,rows,widths)],{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
    const url=URL.createObjectURL(blob), a=document.createElement('a'); a.href=url; a.download=nomFichier; document.body.appendChild(a); a.click();
    setTimeout(()=>{ URL.revokeObjectURL(url); a.remove(); },1000);
  }
  return {octets,telecharger,crc32,colName,sheetXml};
});
