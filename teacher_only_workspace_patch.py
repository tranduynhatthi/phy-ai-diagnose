"""Show only each teacher's own classes: remove obsolete 'Không gian trường' UI.

This runs after the educator and student portals have been fully assembled.
School records/endpoints are intentionally retained for migration/rollback.
There is no deletion or rewrite of learner outcomes or memberships.
"""
from html.parser import HTMLParser
from pathlib import Path
import re

file=Path("/app/app/static/index.html")
html=file.read_text(encoding="utf-8")

class Node:
    def __init__(self,tag,attrs,start,parent=None):
        self.tag=tag;self.attrs=dict(attrs);self.start=start;self.end=None;self.parent=parent
    @property
    def node_id(self):return self.attrs.get("id","")
    @property
    def classes(self):return self.attrs.get("class","").split()

class DOM(HTMLParser):
    def __init__(self,source):
        super().__init__(convert_charrefs=True)
        self.source=source;self.lines=[0];self.nodes=[];self.stack=[]
        for line in source.splitlines(keepends=True):self.lines.append(self.lines[-1]+len(line))
        self.feed(source)
    def source_offset(self):
        line,col=self.getpos()
        return self.lines[line-1]+col
    def handle_starttag(self,tag,attrs):
        if tag in {"br","hr","input","img","meta","link","source","area","wbr","path","circle"}:return
        node=Node(tag,attrs,self.source_offset(),self.stack[-1] if self.stack else None)
        self.nodes.append(node)
        self.stack.append(node)
    def handle_endtag(self,tag):
        for idx in range(len(self.stack)-1,-1,-1):
            if self.stack[idx].tag==tag:
                self.stack[idx].end=self.source.find(">",self.source_offset())+1
                del self.stack[idx:]
                break

tree=DOM(html)
teacher=next((n for n in tree.nodes if n.node_id=="teacherView" and n.end),None)
student=next((n for n in tree.nodes if n.node_id=="studentView" and n.end),None)
if not teacher or not student:raise SystemExit("Teacher/student layout is incomplete")

anchors={"schoolSelect","schoolIdentity","schoolDetailCard","schoolStats"}
owned_ids={"classList","teacherStats","studentProgressRows","studentDetailCard","exportBtn"}
selected=[]
for anchor in sorted(anchors):
    nodes=[n for n in tree.nodes if n.node_id==anchor and teacher.start<n.start<n.end<teacher.end]
    if not nodes:continue
    node=nodes[0]
    # Remove the whole school card, not a single input with an empty label.
    card=node
    while card and ("card" not in card.classes and card.node_id!="teacherView"):
        card=card.parent
    if not card or card.node_id=="teacherView":
        if node.node_id=="schoolDetailCard" and node.end:
            card=node
        else:
            raise SystemExit("School block has no removable card: "+anchor)
    contents=html[card.start:card.end]
    if any(f'id="{ident}"' in contents for ident in owned_ids):
        raise SystemExit("Refusing to delete class dashboard while removing school "+anchor)
    selected.append((card.start,card.end))

if not selected:
    raise SystemExit("No standalone school workspace found to remove")

# Remove the student-only school label, without deleting the self-study UI/card.
for node in tree.nodes:
    if node.node_id in {"studentSchoolLine"} and student.start<node.start<node.end<student.end:
        selected.append((node.start,node.end))

selected.sort()
merged=[]
for a,b in selected:
    if not merged or a>=merged[-1][1]:merged.append((a,b))
    elif b>merged[-1][1]:
        merged[-1]=(merged[-1][0],b)
for a,b in reversed(merged):
    html=html[:a]+html[b:]

# Workspaces no longer load school-level data: only classes assigned to the
# logged-in teacher and their enrolled students.
pattern=re.compile(r"^async function loadTeacher\(\)\{[\s\S]*?^\}\n",re.M)
new_teacher="""async function loadTeacher(){
 const sessionToken=token;
 if(!me||me.role!=='teacher')return;
 if($('teacherWelcome'))$('teacherWelcome').textContent='Xin chào, '+me.display_name;
 // School-wide rosters are deliberately NOT queried.
 if(sessionToken!==token)return;
 await loadTeacherClassesBase();
}
"""
html,n=pattern.subn(lambda _:new_teacher,html,count=1)
if n!=1:raise SystemExit("Could not locate the unique teacher loader")
# Make the remaining section title unambiguous.
html=html.replace("Quản lý lớp và theo dõi tiến độ học tập",
                  "Lớp học của tôi — Quản lý học sinh",1)

# Ensure legacy school API calls cannot be triggered by the teacher's normal
# dashboard path. The helper functions are left available for compatibility
# but have no entry point in the simplified interface.
teacher_part=html.split('<section id="teacherView"',1)[1].split("</section>",1)[0]
for ident in ("schoolSelect","schoolIdentity","schoolDetailCard","schoolStats"):
    if f'id="{ident}"' in teacher_part:raise SystemExit("School control visible in teacher dashboard: "+ident)
for ident in ("classList","studentProgressRows","studentDetailCard"):
    if f'id="{ident}"' not in teacher_part:raise SystemExit("Missing teacher-owned class control: "+ident)
if "await loadSchools();" in html[html.index("async function loadTeacher()"):html.index("async function loadTeacher()")+400]:
    raise SystemExit("School fetch still active in teacher startup")
file.write_text(html,encoding="utf-8")
print("Removed legacy school workspace. Teacher page retains owned classes and student reports.")
