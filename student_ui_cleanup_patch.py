"""Hide irrelevant student-class panel, preserving all DOM IDs and backend data."""
from html.parser import HTMLParser
from pathlib import Path

VOID={"area","base","br","col","embed","hr","img","input","link","meta","param","source","track","wbr"}

class Finder(HTMLParser):
    def __init__(self,source):
        super().__init__()
        self.starts=[0]
        for line in source.splitlines(keepends=True):
            self.starts.append(self.starts[-1]+len(line))
        self.stack=[]
        self.cards=[]
        self.feed(source)
    def handle_starttag(self,tag,attrs):
        if tag in VOID:return
        line,col=self.getpos()
        start=self.starts[line-1]+col
        self.stack.append(dict(tag=tag,attrs=dict(attrs),start=start,
                               end=start+len(self.get_starttag_text()),text=[]))
    def handle_data(self,data):
        for e in self.stack:
            if e["tag"] in ("h2","h3"):e["text"].append(data)
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i]["tag"]!=tag:continue
            heading=self.stack[i]
            if tag in ("h2","h3") and "".join(heading["text"]).strip()=="Lớp học":
                parents=self.stack[:i]
                if any(p["attrs"].get("id")=="studentView" for p in parents):
                    cards=[p for p in parents if "card" in p["attrs"].get("class","").split()]
                    if cards:self.cards.append(cards[-1])
            del self.stack[i:]
            break

def simplify(html):
    if 'data-student-class-panel="hidden"' in html:return html
    cards=Finder(html).cards
    if len(cards)!=1:raise ValueError("Student class card count: "+str(len(cards)))
    card=cards[0]
    tag=html[card["start"]:card["end"]]
    new=tag[:-1]+' data-student-class-panel="hidden" aria-hidden="true">'
    html=html[:card["start"]]+new+html[card["end"]:]
    css='<style id="student-ui-cleanup">#studentView [data-student-class-panel="hidden"]{display:none!important}</style>'
    return html.replace("</head>",css+"</head>",1)

def apply(root=Path("/app")):
    p=Path(root)/"app/static/index.html"
    p.write_text(simplify(p.read_text(encoding="utf8")),encoding="utf8")

if __name__=="__main__":apply()
