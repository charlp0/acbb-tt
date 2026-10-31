const test=require('node:test'),assert=require('node:assert');
const X=require('../shared/xlsx-min.js');
test('xlsx minimal : zip valide, feuille avec en-tête, nombres typés et texte échappé',()=>{
  const u8=X.octets('Test',[['Nom','Pts'],['A & B',644],['C',-12]]);
  assert.deepEqual([...u8.slice(0,4)],[80,75,3,4]);                       // signature zip locale
  const txt=Buffer.from(u8).toString('latin1');
  assert.ok(txt.includes('xl/worksheets/sheet1.xml')&&txt.includes('[Content_Types].xml'));
  const n=txt.lastIndexOf('PK\x05\x06'); assert.ok(n>0,'fin de répertoire central');
  assert.equal(Buffer.from(u8).readUInt16LE(n+10),6,'6 entrées');
  const sheet=X.sheetXml([['Nom','Pts'],['A & B',644]]);
  assert.ok(sheet.includes('<c r="B2"><v>644</v></c>'));
  assert.ok(sheet.includes('A &amp; B'));
  assert.ok(sheet.includes('<c r="A1" t="inlineStr" s="1">'));
  assert.equal(X.colName(27),'AB');
  assert.equal(X.crc32(new TextEncoder().encode('123456789')),0xCBF43926);
});
