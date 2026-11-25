/* ---------- Lector dedicado del RUP (formato Cámara de Comercio): reglas exactas + autoverificación ---------- */
const esRUPNombre=n=>/(^|[^a-z])rup([^a-z]|$)/i.test(n||"");
const numCO=s=>{if(s==null)return null;const t=String(s).replace(/[$\s]/g,"");if(!t||t==="-")return null;const v=Number(t.replace(/\./g,"").replace(",","."));return isNaN(v)?null:v};
const MESES={ENERO:1,FEBRERO:2,MARZO:3,ABRIL:4,MAYO:5,JUNIO:6,JULIO:7,AGOSTO:8,SEPTIEMBRE:9,SETIEMBRE:9,OCTUBRE:10,NOVIEMBRE:11,DICIEMBRE:12};
const fISO=s=>{const m=String(s||"").match(/(\d{4})\/(\d{2})\/(\d{2})/)||String(s||"").match(/(\d{2})\/(\d{2})\/(\d{4})/);if(!m)return null;return m[1].length===4?`${m[1]}-${m[2]}-${m[3]}`:`${m[3]}-${m[2]}-${m[1]}`};
function parsearRUP(pages){
  const V=[];const ok=(item,cond,det)=>V.push({item,ok:!!cond,detalle:det});
  // 1. texto limpio: sin encabezados de página, sin saltos
  const N=pages.length;
  const impresas=new Set();let totalImpresas=null;
  const limpias=pages.map(p=>{const m=p.match(/P[ÁA]GINA:\s*(\d+)\s*DE\s*(\d+)/i);if(m){impresas.add(+m[1]);totalImpresas=+m[2]}
    return p.replace(/CAMARA DE COMERCIO DE BOGOTA\s*SEDE VIRTUAL\s*C[ÓO]DIGO VERIFICACI[ÓO]N:\s*\S+\s*\d{1,2} DE [A-Z]+ DE \d{4}\s*HORA [\d:]+\s*\S+\s*P[ÁA]GINA:\s*\d+\s*DE\s*\d+\s*(\*\s*)+/gi," ")});
  const T=limpias.join("\n").replace(/[ \t]+/g," ");
  const L=T.replace(/\s+/g," ");                 // una sola línea, para campos
  ok("Páginas del PDF leídas",N>0&&pages.every(p=>p.trim().length>20),`${N} páginas con texto${pages.filter(p=>p.trim().length<=20).length?` · ${pages.filter(p=>p.trim().length<=20).length} vacías`:""}`);
  if(totalImpresas){const falt=[];for(let i=1;i<=totalImpresas;i++)if(!impresas.has(i))falt.push(i);ok("Hojas numeradas por la Cámara",!falt.length,`${impresas.size} de ${totalImpresas}${falt.length?" · faltan: "+falt.join(", "):""}`)}
  const g=(re,s=L)=>{const m=s.match(re);return m?m[1].trim():null};
  // 2. identificación y generales
  const ident={nombre:g(/IDENTIFICACION\s*QUE:\s*(.+?)\s*NIT:/),nit:g(/NIT:\s*([\d\s-]+?)\s*NUMERO DEL PROPONENTE/),numero_proponente:g(/NUMERO DEL PROPONENTE EN LA CAMARA DE COMERCIO:\s*(\d+)/),
    fecha_inscripcion:fISO(g(/FECHA DE INSCRIPCION EN EL REGISTRO DE LOS PROPONENTES:\s*([\d\/]+)/)),fecha_ultima_renovacion:fISO(g(/FECHA DE ULTIMA RENOVACION EN EL REGISTRO DE LOS PROPONENTES:\s*([\d\/]+)/)),
    fecha_expedicion:(()=>{const m=pages.join(" ").replace(/\s+/g," ").match(/(\d{1,2}) DE ([A-Z]+) DE (\d{4}) HORA/);return m&&MESES[m[2]]?`${m[3]}-${String(MESES[m[2]]).padStart(2,"0")}-${m[1].padStart(2,"0")}`:null})(),
    codigo_verificacion:g(/C[ÓO]DIGO VERIFICACI[ÓO]N:\s*(\S+)/,pages.join(" ")),
    tamano_empresa:g(/QUE EL INSCRITO SE CLASIFICO COMO:\s*([A-ZÁÉÍÓÚ ]+?)\s*CERTIFICA/),
    domicilio:g(/DIRECCION DEL DOMICILIO PRINCIPAL\s*(.+?)\s*DIRECCION PARA NOTIFICACION/),
    representacion:(L.match(/REPRESENTACION LEGAL(.+?)LA INFORMACION ANTERIOR HA SIDO TOMADA/)||[])[1]?.trim().slice(0,1500)||null};
  ok("Identificación del proponente",ident.nombre&&ident.nit,`${ident.nombre||"?"} · NIT ${ident.nit||"?"} · expedido ${ident.fecha_expedicion||"?"}`);
  // 3. información financiera e indicadores
  const fin={corte:fISO(g(/FECHA DE CORTE DE LA INFORMACI[ÓO]N FINANCIERA:\s*([\d\/]+)/)),activo_corriente:numCO(g(/ACTIVO CORRIENTE:\s*\$?\s*([\d.,]+)/)),activo_total:numCO(g(/ACTIVO TOTAL:\s*\$?\s*([\d.,]+)/)),
    pasivo_corriente:numCO(g(/PASIVO CORRIENTE:\s*\$?\s*([\d.,]+)/)),pasivo_total:numCO(g(/PASIVO TOTAL:\s*\$?\s*([\d.,]+)/)),patrimonio:numCO(g(/PATRIMONIO:\s*\$?\s*(-?[\d.,]+)/)),
    utilidad_operacional:numCO(g(/UTILIDAD\/PERDIDA OPERACIONAL:\s*\$?\s*(-?[\d.,]+)/)),gastos_intereses:numCO(g(/GASTOS DE INTERESES:\s*\$?\s*([\d.,]+)/)),
    indicadores:{liquidez:numCO(g(/INDICE DE LIQUIDEZ:\s*([\d.,]+|INDETERMINADO)/)),endeudamiento:numCO(g(/INDICE DE ENDEUDAMIENTO:\s*([\d.,]+)/)),cobertura_intereses:numCO(g(/CO[R]?BERTURA DE INTERESES:\s*([\d.,]+|INDETERMINADO)/)),
      rentabilidad_patrimonio:numCO(g(/RENTABILIDAD DEL PATRIMONIO:\s*(-?[\d.,]+)/)),rentabilidad_activo:numCO(g(/RENTABILIDAD DEL ACTIVO:\s*(-?[\d.,]+)/))}};
  const camposF=["corte","activo_corriente","activo_total","pasivo_corriente","pasivo_total","patrimonio","utilidad_operacional","gastos_intereses"].filter(k=>fin[k]==null);
  ok("Información financiera",!camposF.length,camposF.length?"faltan: "+camposF.join(", "):`corte ${fin.corte} · 8 de 8 campos`);
  const indF=Object.entries(fin.indicadores).filter(([k,v])=>v==null).map(([k])=>k);
  ok("Indicadores financieros y organizacionales",!indF.length,indF.length?"sin dato: "+indF.join(", "):"5 de 5 indicadores");
  // 4. clasificación UNSPSC inscrita
  const secCla=(T.match(/CERTIFICA:\s*CLASIFICACION\s*\n([\s\S]*?)CERTIFICA:\s*EXPERIENCIA/i)||[])[1]||"";
  const clasificacion=[];
  for(const ln of secCla.split("\n")){const m=ln.match(/\|\s*(\d{2})\s*\|\s*(\d{2})\s*\|\s*(\d{2})\s*\|\s*(\d{2})\s*\|\s*(.*?)\s*\|/);
    if(m)clasificacion.push({codigo:m[1]+m[2]+m[3]+m[4],descripcion:m[5]});else{const c=ln.match(/^\s*\|\s*\|\s*\|\s*\|\s*\|\s*(.*?)\s*\|/);if(c&&clasificacion.length)clasificacion[clasificacion.length-1].descripcion+=c[1]}}
  const filasCla=(secCla.match(/\|\s*\d{2}\s*\|\s*\d{2}\s*\|\s*\d{2}\s*\|\s*\d{2}\s*\|/g)||[]).length;
  ok("Clasificación UNSPSC inscrita",clasificacion.length&&clasificacion.length===filasCla,`${clasificacion.length} clases leídas de ${filasCla} filas`);
  // 5. experiencia: bloques por consecutivo
  const ini=T.search(/CERTIFICA:\s*EXPERIENCIA/i);const finExp=(()=>{const r=T.slice(ini+20).search(/CERTIFICA:/i);return r<0?T.length:ini+20+r})();
  const secExp=ini<0?"":T.slice(ini,finExp);
  const marcas=[...secExp.matchAll(/NUMERO CONSECUTIVO DEL REPORTE DEL CONTRATO EJECUTADO:\s*(\d+)/g)];
  const contratos=[];const problemas=[];
  marcas.forEach((m,i)=>{const b=secExp.slice(m.index,i+1<marcas.length?marcas[i+1].index:secExp.length);const bl=b.replace(/\s+/g," ");
    const cods=[...b.matchAll(/\|\s*(\d{2})\s*\|\s*(\d{2})\s*\|\s*(\d{2})\s*\|\s*(\d{2})\s*\|/g)].map(x=>x[1]+x[2]+x[3]+x[4]);
    const c={consecutivo:+m[1],celebrado_por:(bl.match(/CONTRATO CELEBRADO POR:\s*(.+?)\s*NOMBRE DEL CONTRATISTA/)||[])[1]||null,
      contratista:(bl.match(/NOMBRE DEL CONTRATISTA:\s*(.+?)\s*NOMBRE DEL CONTRATANTE/)||[])[1]||null,
      contratante:(bl.match(/NOMBRE DEL CONTRATANTE:\s*(.+?)\s*VALOR DEL CONTRATO/)||[])[1]||null,
      valor_smmlv:numCO((bl.match(/EXPRESADO EN SMMLV:\s*([\d.,]+)/)||[])[1]),
      porcentaje_participacion:numCO((bl.match(/CONSORCIOS Y UNIONES TEMPORALES:\s*([\d.,]+)\s*%/)||[])[1]),
      unspsc:[...new Set(cods)],filas_unspsc:cods.length};
    c.es_plural=/CONSORCIO|UNION TEMPORAL|SOCIEDAD/i.test(c.celebrado_por||"");
    const f=[];if(!c.contratista)f.push("contratista");if(!c.contratante)f.push("contratante");if(c.valor_smmlv==null)f.push("valor en SMMLV");if(!c.unspsc.length)f.push("códigos UNSPSC");if(c.es_plural&&c.porcentaje_participacion==null)f.push("% de participación");
    if(f.length)problemas.push(`#${c.consecutivo}: falta ${f.join(", ")}`);c.campos_faltantes=f;contratos.push(c)});
  const etiquetas=(secExp.match(/NUMERO CONSECUTIVO DEL REPORTE/g)||[]).length;
  const nums=contratos.map(c=>c.consecutivo);const max=nums.length?Math.max(...nums):0;
  const faltan=[];for(let i=1;i<=max;i++)if(!nums.includes(i))faltan.push(i);const dups=[...new Set(nums.filter((n,i)=>nums.indexOf(n)!==i))];
  ok("Contratos de experiencia: todos los consecutivos",contratos.length&&contratos.length===etiquetas&&!faltan.length&&!dups.length,`${contratos.length} contratos (consecutivos 1 a ${max})${faltan.length?" · faltan: "+faltan.join(", "):""}${dups.length?" · repetidos: "+dups.join(", "):""}`);
  ok("Contratos de experiencia: campos completos",!problemas.length,problemas.length?problemas.join(" · "):"contratista, contratante, valor SMMLV, % (si es plural) y UNSPSC en todos");
  ok("Códigos UNSPSC por contrato",contratos.every(c=>c.unspsc.length),`${contratos.reduce((s,c)=>s+c.unspsc.length,0)} códigos en total`);
  // 6. historial de inscripción / renovaciones
  const historial=[...L.matchAll(/QUE EL DIA (\d{1,2}) DEL MES DE ([A-Z]+) DE (\d{4}) EL PROPONENTE ([A-Z]+) EL REGISTRO UNICO DE PROPONENTES BAJO EL NUMERO (\d+)/g)].map(m=>({fecha:MESES[m[2]]?`${m[3]}-${String(MESES[m[2]]).padStart(2,"0")}-${m[1].padStart(2,"0")}`:null,accion:m[4],registro:m[5]}));
  ok("Historial de inscripción y renovaciones",historial.length>0,`${historial.length} actuaciones`);
  // 7. reportes de las entidades (adjudicados, en ejecución, ejecutados, multas, sanciones, inhabilidades)
  const iRep=L.search(/REPORTE DE LA INFORMACI[ÓO]N POR PARTE DE LAS ENTIDADES/);
  const secRep=iRep<0?"":L.slice(iRep);
  const reportes=[];let grupo="";
  const partes=secRep.split(/(?=CONTRATOS ADJUDICADOS|CONTRATOS EN EJECUCION|CONTRATOS EJECUTADOS|MULTAS|SANCIONES|INHABILIDADES|ENTIDAD CONTRATANTE:)/);
  for(const p of partes){const gm=p.match(/^(CONTRATOS ADJUDICADOS|CONTRATOS EN EJECUCION|CONTRATOS EJECUTADOS|MULTAS|SANCIONES|INHABILIDADES)/);if(gm){grupo=gm[1];continue}
    if(!p.startsWith("ENTIDAD CONTRATANTE:"))continue;const G=re=>(p.match(re)||[])[1]?.trim()||null;
    reportes.push({grupo,entidad:G(/ENTIDAD CONTRATANTE:\s*(.+?)\s*MUNICIPIO:/),municipio:G(/MUNICIPIO:\s*(.+?)\s*NUMERO DEL CONTRATO/),numero_contrato:G(/NUMERO DEL CONTRATO:\s*(\S+)/),
      fecha_adjudicacion:fISO(G(/FECHA DE ADJUDICACION:\s*([\d\/]+)/)),fecha_inicio:fISO(G(/FECHA INICIO:\s*([\d\/]+)/)),fecha_terminacion:fISO(G(/FECHA TERMINACION:\s*([\d\/]+)/)),
      valor_cop:numCO(G(/VALOR (?:DEL CONTRATO|INICIAL DEL CONTRATO) (?:EN PESOS|\(EN PESOS\)):?\s*([\d.,]+)/)),valor_final_cop:numCO(G(/VALOR FINAL DEL CONTRATO PAGADO \(EN PESOS\):\s*([\d.,]+|-)/)),
      clasificacion:[...((p.match(/CLASIFICACION CONTRATO(.*?)FECHA DE INSCRIPCION/)||[])[1]||"").matchAll(/(\d{5,8})\s+[A-ZÁÉÍÓÚÑ]/g)].map(x=>x[1]),fecha_inscripcion:fISO(G(/FECHA DE INSCRIPCION:\s*([\d\/]+)/)),registro:G(/NUMERO DE REGISTRO EN EL LIBRO I DE LOS PROPONENTES:\s*(\d+)/)})}
  const etiqRep=(secRep.match(/ENTIDAD CONTRATANTE:/g)||[]).length;
  ok("Contratos reportados por entidades",reportes.length===etiqRep,`${reportes.length} reportes (${["CONTRATOS ADJUDICADOS","CONTRATOS EN EJECUCION","CONTRATOS EJECUTADOS","MULTAS","SANCIONES","INHABILIDADES"].map(k=>`${k.toLowerCase().replace("contratos ","")}: ${reportes.filter(r=>r.grupo===k).length}`).join(", ")})`);
  const multas=/MULTAS|SANCIONES|INHABILIDADES/.test(secRep)?reportes.filter(r=>/MULTAS|SANCIONES|INHABILIDADES/.test(r.grupo)):[];
  return {formato:"camara_comercio",completo:V.every(v=>v.ok),verificacion:V,identificacion:ident,financiero:fin,fecha_corte_financiero:fin.corte,fecha_expedicion:ident.fecha_expedicion,
    clasificacion,contratos,faltantes:faltan,_secExp:secExp,historial,reportes_entidades:reportes,multas_sanciones:multas,paginas:N,hojas:totalImpresas,caracteres:T.length};
}
