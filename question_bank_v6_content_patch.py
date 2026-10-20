"""Replace 8 same-template MCQs with new SGK-grounded misconception probes.

Source reference: supplied Vật lí 12 Kết nối tri thức PDF, printed pages
66-70, 101-102, 106, 108. Each item is versioned; its original remains
available in LEGACY_QUESTIONS for historical responses.
"""
from pathlib import Path
import sys

DATA_MODULE = r'''"""Manually authored V6 science probes, conservative item-level references."""
from copy import deepcopy
from .quality_v5 import LEGACY_QUESTIONS
from .content_audit import validate_questions

# A changed question is *never* substituted behind the same stable ID.
# Replacements draw from near-number-clone clusters; old items remain addressable.
PROBES = {
    "EXT-16-M04": {
        "error":"TT-13", "level":"TH", "context":"Cuộn dây quay có hai đầu hở",
        "prompt":"Một cuộn dây có hai đầu để hở được quay trong từ trường sao cho từ thông qua các vòng dây biến thiên theo thời gian. Trong mô hình mạch hở lí tưởng, nhận xét nào đúng?",
        "options":[
            "Không thể xuất hiện suất điện động cảm ứng vì hai đầu cuộn dây hở.",
            "Có thể xuất hiện suất điện động cảm ứng, nhưng không có dòng điện chạy thành mạch kín.",
            "Dòng điện cảm ứng luôn tăng vô hạn vì mạch hở có điện trở lớn.",
            "Chỉ có suất điện động cảm ứng khi từ thông không đổi."
        ],
        "answer":1,
        "explain":"Từ thông biến thiên có thể tạo suất điện động cảm ứng. Dòng điện chạy thành mạch kín đòi hỏi có đường dẫn điện kín; không được đồng nhất suất điện động và dòng điện.",
        "source_page":70
    },
    "EXT-16-M05": {
        "error":"TT-13", "level":"TH", "context":"Ngắt khóa trong mạch cảm ứng",
        "prompt":"Một khung dây có từ thông biến thiên đang nối với điện trở ngoài qua khóa K. Người ta mở khóa K để mạch bị hở, trong khi từ thông qua khung vẫn tiếp tục biến thiên. Kết luận nào đúng trong mô hình lí tưởng?",
        "options":[
            "Suất điện động cảm ứng lập tức bằng 0 do khóa đã mở.",
            "Dòng điện qua khóa tăng vì điện trở mạch lớn.",
            "Từ thông ngừng biến thiên ngay khi mở khóa.",
            "Dòng điện qua mạch ngoài bằng 0, nhưng suất điện động cảm ứng vẫn có thể khác 0."
        ],
        "answer":3,
        "explain":"Mở khóa làm mất dòng điện qua mạch ngoài; sự biến thiên từ thông vẫn là nguyên nhân làm xuất hiện suất điện động cảm ứng.",
        "source_page":70
    },
    "EXT-22-M04": {
        "error":"HN-07", "level":"NB", "context":"Urani hấp thụ neutron và phân tách",
        "prompt":"Hạt nhân urani-235 hấp thụ một neutron, chuyển sang trạng thái kích thích rồi phân tách thành hai hạt nhân có khối lượng nhỏ hơn, đồng thời phát ra một số neutron. Quá trình này gọi là gì?",
        "options":["Phản ứng phân hạch.","Phản ứng nhiệt hạch.","Phóng xạ gamma.","Hiện tượng ion hóa nguyên tử."],
        "answer":0,
        "explain":"Phân hạch là quá trình một hạt nhân nặng phân tách thành các hạt nhân nhẹ hơn, có thể phát neutron; không phải quá trình tổng hợp hạt nhân nhẹ.",
        "source_page":101
    },
    "EXT-22-M05": {
        "error":"HN-07", "level":"TH", "context":"Kết hợp các hạt nhân nhẹ",
        "prompt":"Hai hạt nhân nhẹ có động năng đủ lớn tiến lại gần và kết hợp thành một hạt nhân nặng hơn, đồng thời giải phóng năng lượng. Tên quá trình phù hợp nhất là gì?",
        "options":["Phóng xạ beta.","Phản ứng tổng hợp hạt nhân (nhiệt hạch).","Phân hạch hạt nhân nặng.","Phát xạ photon do electron chuyển mức."],
        "answer":1,
        "explain":"Nhiệt hạch là sự tổng hợp các hạt nhân nhẹ thành hạt nhân nặng hơn; cần phân biệt với phân hạch của hạt nhân nặng.",
        "source_page":102
    },
    "EXT-23-M02": {
        "error":"HN-13", "level":"TH", "context":"Hoạt độ sau một chu kì bán rã",
        "prompt":"Một mẫu chỉ chứa một đồng vị phóng xạ có hoạt độ ban đầu H0. Sau đúng một chu kì bán rã, giả sử không có bổ sung hạt nhân phóng xạ, hoạt độ của mẫu bằng bao nhiêu?",
        "options":["2H0.","H0.","H0/2.","H0/4."],
        "answer":2,
        "explain":"Với cùng đồng vị, hằng số phóng xạ không đổi và hoạt độ tỉ lệ thuận với số hạt nhân chưa phân rã. Sau một chu kì bán rã, cả số hạt còn lại và hoạt độ đều giảm còn một nửa.",
        "source_page":108
    },
    "EXT-23-M03": {
        "error":"HN-13", "level":"VD", "context":"So sánh hai mẫu cùng đồng vị",
        "prompt":"Hai mẫu A và B chỉ chứa cùng một đồng vị phóng xạ. Tại thời điểm khảo sát, số hạt nhân chưa phân rã trong mẫu A gấp 3 lần mẫu B. Tỉ số hoạt độ HA/HB của hai mẫu là bao nhiêu?",
        "options":["1/3.","1.","3.","9."],
        "answer":2,
        "explain":"Hai mẫu cùng đồng vị nên cùng hằng số phóng xạ. Hoạt độ tỉ lệ với số hạt nhân chưa phân rã; số hạt A gấp ba thì hoạt độ A cũng gấp ba.",
        "source_page":108
    },
    "EXT-23-M04": {
        "error":"HN-14", "level":"TH", "context":"Giấy nhôm và chì chắn tia",
        "prompt":"Trong hình minh họa khả năng đâm xuyên của các tia phóng xạ, tia nào dễ bị chặn bởi tờ giấy, trong khi tia gamma có khả năng xuyên qua giấy và một lớp nhôm mỏng mạnh hơn?",
        "options":["Tia gamma.","Tia beta.","Tia X.","Tia alpha."],
        "answer":3,
        "explain":"Tia alpha có khả năng đâm xuyên kém và bị chặn bởi một tờ giấy; tia gamma đâm xuyên mạnh hơn đáng kể. Tia X không thuộc ba tia alpha, beta, gamma được so sánh trong bài.",
        "source_page":106
    },
    "EXT-23-M05": {
        "error":"HN-14", "level":"TH", "context":"Phân biệt ion hóa và đâm xuyên",
        "prompt":"Theo so sánh định tính các tia alpha, beta và gamma trong chương trình Vật lí phổ thông, phát biểu nào đúng?",
        "options":[
            "Tia alpha thường ion hóa mạnh nhưng đâm xuyên kém.",
            "Tia alpha luôn đâm xuyên mạnh nhất vì có khối lượng lớn.",
            "Tia gamma bị chặn hoàn toàn bởi một tờ giấy mỏng.",
            "Tia beta có khả năng đâm xuyên kém hơn tia alpha trong mọi trường hợp."
        ],
        "answer":0,
        "explain":"Trong so sánh định tính ở SGK, tia alpha ion hóa mạnh và đâm xuyên yếu; tia gamma đâm xuyên mạnh. Không đồng nhất độ ion hóa với độ đâm xuyên.",
        "source_page":106
    },
}


def apply_v6_content(data):
    if data.get("version")!="2026.10-1000q-v5-tf-balanced":
        raise ValueError("V6 probe replacements require exactly the checked V5 bank")
    rows={q["id"]:q for q in data["questions"]}
    if len(rows)!=1000:
        raise ValueError("V6 base bank must contain 1000 unique questions")
    seen=set()
    for old_id, spec in PROBES.items():
        if old_id not in rows or old_id in seen:
            raise ValueError("V6 source question missing or duplicated: "+old_id)
        seen.add(old_id)
        existing=rows[old_id]
        if existing["type"]!="mcq" or existing.get("lesson") not in ("Bài 16","Bài 22","Bài 23"):
            raise ValueError("V6 replacement target no longer matches audited item: "+old_id)
        if old_id+"-V6" in rows:
            raise ValueError("V6 new question ID already exists: "+old_id)
        ontology=next((x for x in data["errors"] if x["id"]==spec["error"]),None)
        if ontology is None:
            raise ValueError("V6 unknown misconception: "+spec["error"])
        old=deepcopy(existing)
        LEGACY_QUESTIONS[old_id]=old
        item={
            "id":old_id+"-V6",
            "chapter":ontology["chapter"],
            "lesson":ontology["lesson"],
            "type":"mcq",
            "level":spec["level"],
            "context":spec["context"],
            "prompt":spec["prompt"],
            "options":list(spec["options"]),
            "answer":spec["answer"],
            "explain":spec["explain"],
            "error":spec["error"],
            "diagnostic":True,
            "source_page":spec["source_page"],
            "source_file":"SGK Vật lí 12 – Kết nối tri thức (PDF người dùng cung cấp)",
            "source_topic":"Câu chẩn đoán biên soạn mới từ kiến thức tương ứng trong SGK",
            "verified":False,
            "review_status":"SGK-concept-crosschecked; pending independent educator sign-off",
            "legacy_id":old_id,
        }
        if item["chapter"] != old["chapter"]:
            raise ValueError("V6 replacement moves across chapters: "+old_id)
        existing.clear()
        existing.update(item)
    validate_questions(data)
    data["version"]="2026.10-1000q-v6-content-evidence"
    data.setdefault("audit",{})["v6_content"]={
        "replacements":len(PROBES),
        "old_ids":list(PROBES),
        "reference_pages_printed":{q["id"]:q["source_page"] for q in data["questions"] if q.get("legacy_id") in PROBES},
        "science_review":"Concept cross-check against supplied SGK images; not an independent teacher-panel review.",
        "purpose":"Fill all 4 codes previously lacking independent diagnostic contexts, without changing 1000-question total.",
    }
'''


def apply(root=Path("/app")):
    root=Path(root)
    p=root/"app/question_bank.py"
    source=p.read_text(encoding="utf-8")
    anchor='        apply_v5_rebalance(self.data)\n'
    hook='        from .quality_v6_content import apply_v6_content\n        apply_v6_content(self.data)\n'
    if hook not in source:
        if source.count(anchor)!=1:
            raise RuntimeError("V6 replacement point not found after V5 audit")
        source=source.replace(anchor,anchor+hook,1)
    (root/"app/quality_v6_content.py").write_text(DATA_MODULE,encoding="utf-8")
    p.write_text(source,encoding="utf-8")
    print("V6 source-grounded misconception probes installed")

if __name__=="__main__":
    apply(Path(sys.argv[1]) if len(sys.argv)>1 else Path("/app"))
