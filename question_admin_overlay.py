"""Attach approved managed questions to NEW practice selections, keeping past IDs immutable.

No changes to the protected 1,000-question source data. Old session question IDs
remain answerable after a new revision has been published or a row archived.
"""
from __future__ import annotations
import re
import os
from sqlalchemy import select
from sqlalchemy.orm import Session
from .question_admin_store import ManagedQuestion

_VERSION=re.compile(r"^(QMG-[A-F0-9]{16})-v([1-9][0-9]*)$")

class VersionedIndex(dict):
    def __init__(self, initial,engine):
        super().__init__(initial)
        self._qa_engine=engine

    def __missing__(self, key):
        m=_VERSION.fullmatch(str(key))
        if not m: raise KeyError(key)
        with Session(self._qa_engine) as db:
            row=db.get(ManagedQuestion,m.group(1))
            if row:
                for version in (row.history_json or []):
                    if version.get("id")==key:
                        self[key]=version
                        return version
        raise KeyError(key)

    def get(self,key,default=None):
        # dict.get() does NOT call __missing__, but legacy grade/report routes use it.
        try: return self[key]
        except KeyError: return default

def install_overlay(bank,engine):
    if getattr(bank,"_question_admin_installed",False):
        return
    static_pool=bank.pool
    bank._question_admin_base_pool=static_pool
    bank.by_id=VersionedIndex(bank.by_id,engine)
    def approved_pool(*args,**kwargs):
        baseline=list(static_pool(*args,**kwargs))
        if os.getenv("QUESTION_BANK_PUBLISH_ENABLED","false").lower() not in ("true","1","yes","on"):
            # Rollback must hide new selections but still resolve published
            # immutable IDs from ongoing and historical sessions via by_id.get().
            return baseline
        chapter=args[0] if len(args)>0 else kwargs.get("chapter")
        scope=args[1] if len(args)>1 else kwargs.get("scope")
        lesson=args[2] if len(args)>2 else kwargs.get("lesson")
        diagnostic_only=args[3] if len(args)>3 else kwargs.get("diagnostic_only",False)
        try:
            with Session(engine) as db:
                managed=db.execute(select(ManagedQuestion).where(
                    ManagedQuestion.status.in_(("published","draft","submitted","archive_requested","archived")),
                )).scalars().all()
        except Exception:
            # Bank stays usable if the optional managed table is not provisioned.
            return baseline
        excluded=set()
        supplemental=[]
        for row in managed:
            if row.source_id and (row.published_json is not None or row.status=="archived"):
                excluded.add(row.source_id)
            # An approved archive retires the source, but never destroys old IDs.
            if row.status=="archived": continue
            question=row.published_json
            if not isinstance(question,dict):continue
            if chapter and question.get("chapter")!=chapter: continue
            if scope=="lesson" and lesson and question.get("lesson")!=lesson:continue
            if diagnostic_only and not question.get("diagnostic",True):continue
            bank.by_id[question["id"]]=question
            supplemental.append(question)
        return [q for q in baseline if q.get("id") not in excluded]+supplemental
    bank.pool=approved_pool
    bank._question_admin_installed=True
