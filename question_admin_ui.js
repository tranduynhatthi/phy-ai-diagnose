/* PHY-AI Question Bank administrator UI. Never displays in student mode. */
(function(){
"use strict";
const $=id=>document.getElementById(id);
let qa={current:null,ontology:[],page:1,limit:20,total:0};
const e=s=>String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const notice=(msg,bad)=>{let n=$("qaNotice");if(n){n.textContent=msg;n.style.color=bad?"#9c1725":"#276749";}};
async function apiQA(path,opt){return api(path,opt||{})}
function scopes(){
 let chapters=[...new Set(qa.ontology.map(x=>x.chapter).filter(Boolean))];
 $("qaChapter").innerHTML=chapters.map(x=>'<option>'+e(x)+'</option>').join("");
 $("qaFilterChapter").innerHTML='<option value="">Tất cả</option>'+chapters.map(x=>'<option>'+e(x)+'</option>').join("");
 lessonChange();
}
function lessonChange(){
 let chapter=$("qaChapter").value;
 let lessons=[...new Set(qa.ontology.filter(x=>x.chapter===chapter).map(x=>x.lesson).filter(Boolean))];
 $("qaLesson").innerHTML=lessons.map(x=>'<option>'+e(x)+'</option>').join("");errorsChange();
}
function errorsChange(){
 let ch=$("qaChapter").value,ls=$("qaLesson").value;
 $("qaError").innerHTML='<option value="">Không gắn lỗi (chỉ luyện tập)</option>'+
 qa.ontology.filter(x=>x.chapter===ch&&x.lesson===ls)
 .map(x=>'<option value="'+e(x.id)+'">'+e(x.id+" — "+x.title)+'</option>').join("");
}
function typeChange(){
 let typ=$("qaType").value;
 $("qaMcqFields").style.display=typ==="mcq"?"block":"none";
 $("qaTfFields").style.display=typ==="tf"?"block":"none";
 $("qaShortFields").style.display=typ==="short"?"block":"none";
}
function newDraft(){
 qa.current=null;$("qaEditor").style.display="block";
 $("qaEditorTitle").textContent="Thêm câu hỏi";
 for(const id of ["qaSource","qaPrompt","qaContext","qaExplain","qaOptions","qaShortAnswer","qaUnit"])$(id).value="";
 $("qaSource").disabled=false;
 $("qaType").value="mcq";$("qaMcqAnswer").value="A";$("qaTolerance").value="0.01";$("qaDiagnostic").checked=false;
 $("qaStatements").value='[{"text":"","answer":true,"explain":""},{"text":"","answer":false,"explain":""},{"text":"","answer":true,"explain":""},{"text":"","answer":false,"explain":""}]';
 lessonChange();typeChange();$("qaSaveBtn").disabled=false;
}
async function edit(id){
 try{
 let row=await apiQA("/api/admin/question-bank/"+encodeURIComponent(id));qa.current=row;
 let d=row.draft||{};
 $("qaEditor").style.display="block";
 $("qaEditorTitle").textContent="Chỉnh sửa: "+id+" ("+row.status+")";
 $("qaSource").value=row.status==="base"?id:row.source_id||"";
 $("qaSource").disabled=true;
 $("qaChapter").value=d.chapter;lessonChange();
 $("qaLesson").value=d.lesson;errorsChange();
 $("qaType").value=d.type||"mcq";typeChange();
 $("qaPrompt").value=d.prompt||"";$("qaContext").value=d.context||"";$("qaExplain").value=d.explain||"";
 $("qaOptions").value=(d.options||[]).join("\n");
 $("qaMcqAnswer").value="ABCD"[d.answer]||"A";
 $("qaStatements").value=JSON.stringify(d.statements||[],null,2);
 $("qaShortAnswer").value=d.type==="short"?d.answer:"";
 $("qaTolerance").value=d.tolerance||0.01;$("qaUnit").value=d.unit||"";
 $("qaError").value=d.error||"";$("qaDiagnostic").checked=!!d.diagnostic;
 $("qaSaveBtn").disabled=row.status==="archived";
 }catch(err){notice(err.message,true)}
}
function payload(){
 let typ=$("qaType").value;
 let p={chapter:$("qaChapter").value,lesson:$("qaLesson").value,type:typ,
 prompt:$("qaPrompt").value,context:$("qaContext").value,explain:$("qaExplain").value,
 error:$("qaError").value,diagnostic:$("qaDiagnostic").checked};
 if(typ==="mcq"){
 p.options=$("qaOptions").value.split(/\r?\n/).map(x=>x.trim());
 p.answer=$("qaMcqAnswer").value;
 }else if(typ==="tf"){
 try{p.statements=JSON.parse($("qaStatements").value);}
 catch(_){throw Error("Mệnh đề Đúng/Sai phải là JSON hợp lệ")}
 }else{
 p.answer=$("qaShortAnswer").value;p.tolerance=$("qaTolerance").value;p.unit=$("qaUnit").value;
 }
 return p;
}
async function save(){
 try{
 let question=payload(),r;
 if(qa.current&&qa.current.status!=="base"){
 r=await apiQA("/api/admin/question-bank/"+encodeURIComponent(qa.current.id),{
 method:"PUT",body:JSON.stringify({question,expected_revision:qa.current.revision})});
 }else{
 r=await apiQA("/api/admin/question-bank",{
 method:"POST",body:JSON.stringify({source_id:$("qaSource").value.trim()||null,question})});
 }
 qa.current=r;notice("Đã lưu bản nháp "+r.id+". Cần gửi duyệt trước khi công bố.");
 await list();await edit(r.id);
 }catch(err){notice(err.message,true)}
}
async function action(id,verb,revision){
 if(!confirm("Xác nhận "+verb+" cho câu "+id+"?"))return;
 try{
 let r=await apiQA("/api/admin/question-bank/"+encodeURIComponent(id)+"/"+verb,{
 method:"POST",body:JSON.stringify({expected_revision:revision})});
 notice("Đã cập nhật: "+r.status);
 await list();if(qa.current&&qa.current.id===id)await edit(id);
 }catch(err){notice(err.message,true)}
}
function button(label,cb){
 const el=document.createElement("button");el.type="button";el.className="btn secondary";
 el.textContent=label;el.onclick=cb;return el;
}
async function list(){
 try{
 let qs=new URLSearchParams({page:qa.page,limit:qa.limit,chapter:$("qaFilterChapter").value,
 status:$("qaFilterStatus").value,q:$("qaFind").value.trim()});
 let res=await apiQA("/api/admin/question-bank?"+qs);
 qa.total=res.total;
 $("qaPage").textContent="Trang "+qa.page+" · "+res.total+" câu";
 $("qaPrev").disabled=qa.page<=1;$("qaNext").disabled=qa.page*qa.limit>=res.total;
 let tb=$("qaRows");tb.replaceChildren();
 for(let item of res.items){
 let tr=document.createElement("tr");
 for(const val of [item.id,item.chapter+" / "+item.lesson,item.type,item.title,
 item.error||"—",item.status]){
 let td=document.createElement("td");td.textContent=val;tr.appendChild(td);
 }
 let a=document.createElement("td");a.appendChild(button("Xem/Sửa",()=>edit(item.id)));
 if(item.status==="draft")a.appendChild(button("Gửi duyệt",()=>action(item.id,"submit",item.revision)));
 if(item.status==="submitted"||item.status==="archive_requested")
 a.appendChild(button("Duyệt",()=>action(item.id,"approve",item.revision)));
 if(item.status!=="base"&&item.status!=="archived"&&item.status!=="archive_requested")
 a.appendChild(button("Ẩn/Xóa",()=>action(item.id,"archive-request",item.revision)));
 tr.appendChild(a);tb.appendChild(tr);
 }
 }catch(err){notice(err.message,true)}
}
async function download(){
 try{
 let r=await fetch("/api/admin/question-bank/template.xlsx",{headers:{Authorization:"Bearer "+token}});
 if(!r.ok)throw Error("Không tải được mẫu Excel");
 let u=URL.createObjectURL(await r.blob());let a=document.createElement("a");a.href=u;
 a.download="phyai-question-template.xlsx";document.body.appendChild(a);a.click();a.remove();
 setTimeout(()=>URL.revokeObjectURL(u),500);
 }catch(err){notice(err.message,true)}
}
async function upload(){
 const f=$("qaImport").files[0];
 if(!f||!/\.xlsx$/i.test(f.name)||f.size>3145728){notice("Chọn file XLSX dưới 3 MB",true);return}
 if(!confirm("Nhập file thành bản nháp, chưa công bố?"))return;
 try{
 let r=await fetch("/api/admin/question-bank/import-xlsx",{
 method:"POST",headers:{Authorization:"Bearer "+token,
 "Content-Type":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
 body:await f.arrayBuffer()});
 let j=await r.json();if(!r.ok)throw Error(j.detail||"Nhập Excel thất bại");
 notice("Đã nhập "+j.imported+" câu, tất cả là bản nháp.");qa.page=1;await list();
 }catch(err){notice(err.message,true)}
}
window.qaOpen=async function(){
 const p=$("questionAdminRoot");
 p.style.display=p.style.display==="none"?"block":"none";
 if(p.style.display==="none")return;
 try{
 const state=await apiQA("/api/admin/question-bank/status");
 qa.ontology=await apiQA("/api/admin/question-bank/ontology");
 scopes();
 $("qaMode").textContent=state.published_in_practice?
 "Bản được duyệt đang có hiệu lực trong các phiên luyện tập/chẩn đoán mới.":
 "Đang ở chế độ an toàn: câu duyệt lưu PostgreSQL nhưng chưa thay ngân hàng học sinh.";
 qa.page=1;await list();
 }catch(err){notice(err.message,true)}
};
window.qaNew=()=>newDraft();window.qaSave=()=>save();
window.qaRefresh=()=>{qa.page=1;list()};
window.qaPage=d=>{qa.page=Math.max(1,qa.page+d);list()};
window.qaChapterChanged=()=>lessonChange();window.qaLessonChanged=()=>errorsChange();
window.qaTypeChanged=()=>typeChange();
window.qaTemplate=()=>download();window.qaImport=()=>upload();
})();