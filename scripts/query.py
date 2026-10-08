#!/usr/bin/env python3
"""Read-only query CLI over viewer/livemcq.db.

Usage:
  python3 scripts/query.py stats
  python3 scripts/query.py exam <id|substring>
  python3 scripts/query.py exam-questions <exam_id> [--limit N] [--offset N]
  python3 scripts/query.py qid <qid>
  python3 scripts/query.py search <term>... [-l LIMIT]
  python3 scripts/query.py audio
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "viewer" / "livemcq.db"


def connect():
    if not DB.exists():
        sys.exit(f"database not found: {DB}\n(run scripts/build_sqlite.py first)")
    return sqlite3.connect(str(DB))


def letter(i):
    return chr(ord("A") + i) if isinstance(i, int) and i >= 0 else "?"


def fmt_options(options_json):
    try:
        opts = json.loads(options_json) if options_json else []
    except json.JSONDecodeError:
        return options_json or ""
    if not isinstance(opts, list):
        return str(opts)
    return "\n".join(f"  {letter(i)}. {o}" for i, o in enumerate(opts))


def show_question(row, position=None):
    qid, question, options_json, answer_index, answer_text = row
    print(f"  [{position}] {qid}")
    print(f"    {question}")
    body = json.loads(options_json) if options_json else []
    print(fmt_options(options_json))
    if answer_text:
        ans = f"{answer_text}"
    else:
        ans = f"{letter(answer_index)}" if answer_index is not None else "?"
    print(f"    answer: {ans}")
    print()


def cmd_stats(db):
    print(f"{'exam':>10}  {db.execute('SELECT COUNT(*) FROM exam').fetchone()[0]}")
    print(f"{'exam with content':>10}  {db.execute('SELECT COUNT(*) FROM exam WHERE has_content=1').fetchone()[0]}")
    print(f"{'subject':>10}  {db.execute('SELECT COUNT(*) FROM subject').fetchone()[0]}")
    print(f"{'question':>10}  {db.execute('SELECT COUNT(*) FROM question').fetchone()[0]}")
    print(f"{'exam_question rows':>10}  {db.execute('SELECT COUNT(*) FROM exam_question').fetchone()[0]}")
    print(f"{'video':>10}  {db.execute('SELECT COUNT(*) FROM video').fetchone()[0]}")
    print(f"{'video series':>10}  {db.execute('SELECT COUNT(*) FROM video_series').fetchone()[0]}")
    print(f"{'pdf':>10}  {db.execute('SELECT COUNT(*) FROM pdf').fetchone()[0]}")
    print(f"{'media rows':>10}  {db.execute('SELECT COUNT(*) FROM media_url').fetchone()[0]}")
    audio = db.execute("SELECT COUNT(*) FROM question WHERE is_audio=1").fetchone()[0]
    print(f"{'audio-flagged q':>10}  {audio}")
    no_ans = db.execute("SELECT COUNT(*) FROM question WHERE answer_index IS NULL").fetchone()[0]
    print(f"{'no-answer q':>10}  {no_ans}")


def cmd_exam(db, key, limit):
    rows = db.execute(
        """SELECT e.id, e.title, s.name, e.date, e.question_number, e.has_content, e.slug
           FROM exam e LEFT JOIN subject s ON s.id = e.subject_id
           WHERE e.id = ? OR e.title LIKE ? OR e.slug LIKE ?
           ORDER BY e.date DESC LIMIT ?""",
        (int(key) if key.isdigit() else -1, f"%{key}%", f"%{key}%", limit),
    ).fetchall()
    if not rows:
        sys.exit(f"no exam matches {key!r}")
    for (eid, title, subj, date, qnum, has, slug) in rows:
        tag = "content" if has else "empty"
        print(f"{eid}\t{date}\t{tag}\t{subj}\tq{qnum}\t{title}")


def cmd_exam_questions(db, exam_id, limit, offset):
    rows = db.execute(
        """SELECT q.qid, q.question, q.options_json, q.answer_index, q.answer_text,
                  eq.position, eq.subject_group
           FROM exam_question eq JOIN question q ON q.qid = eq.qid
           WHERE eq.exam_id = ? ORDER BY eq.position LIMIT ? OFFSET ?""",
        (exam_id, limit, offset),
    ).fetchall()
    for r in rows:
        qid, question, ojson, ai, atext, pos, sgrp = r
        head = f"[{pos}] {qid}" + (f"  <{sgrp}>" if sgrp else "")
        print(head)
        print(f"    {question}")
        print(fmt_options(ojson))
        print("    answer:", atext or letter(ai) or "?")
        print()


def cmd_qid(db, qid):
    r = db.execute(
        "SELECT qid, question, options_json, answer_index, answer_text, explanation_html, "
        "is_audio, source, has_bank, slug, syllabus "
        "FROM question WHERE qid = ?",
        (qid,),
    ).fetchone()
    if not r:
        sys.exit(f"no question with qid {qid!r}")
    qid, question, ojson, ai, atext, expl, audio, src, bank, slug, syl = r
    print(f"qid:     {qid}")
    print(f"audio:   {bool(audio)}   bank: {bool(bank)}   source exam: {src}")
    if slug:
        print(f"slug:    {slug}")
    if syl:
        print(f"syllabus:{syl}")
    print(f"Q:       {question}")
    print(fmt_options(ojson))
    print(f"answer:  {atext or letter(ai) or '?'}")
    if expl:
        import re
        text = re.sub(r"<[^>]+>", " ", expl)
        text = re.sub(r"\s+", " ", text).strip()
        print(f"explain: {text}")


def cmd_search(db, terms, limit):
    query = " ".join(terms)
    if not query.strip():
        sys.exit("search needs a term")
    q = '"' + query.replace('"', "") + '"'
    try:
        rows = db.execute(
            """SELECT question.qid, question.question, question.options_json,
                      question.answer_index, question.answer_text, question.has_bank,
                      fts_doc.qid
               FROM question_fts
               JOIN fts_doc ON fts_doc.rowid = question_fts.rowid
               JOIN question ON question.qid = fts_doc.qid
               WHERE question_fts MATCH ?
               ORDER BY rank LIMIT ?""",
            (q, limit),
        ).fetchall()
    except sqlite3.OperationalError as e:
        sys.exit(f"match failed on {q!r}: {e}")
    print(f"{len(rows)} result(s) for {query!r}")
    for (qid, question, ojson, ai, atext, bank, _) in rows:
        where = "bank" if bank else "routine-only"
        print(f"{qid}\t[{where}]")
        print(f"    {question}")
    if not rows:
        sys.exit(0)


def cmd_audio(db, limit):
    print(f"questions flagged is_audio: {db.execute('SELECT COUNT(*) FROM question WHERE is_audio=1').fetchone()[0]}")
    print(f"of total:                   {db.execute('SELECT COUNT(*) FROM question').fetchone()[0]}")
    rows = db.execute(
        """SELECT qid, question, source FROM question WHERE is_audio=1 LIMIT ?""",
        (limit,),
    ).fetchall()
    for qid, question, src in rows:
        print(f"{qid}\t{src}\t{question[:90]}")
    if len(rows) == limit:
        print(f"(...) showing first {limit}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Query the LiveMCQ recovery SQLite DB")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("stats")

    p = sub.add_parser("exam", help="find exams by id or title substring")
    p.add_argument("key")
    p.add_argument("-l", "--limit", type=int, default=30)

    p = sub.add_parser("exam-questions", help="dump a single exam's questions")
    p.add_argument("exam_id", type=int)
    p.add_argument("-l", "--limit", type=int, default=200)
    p.add_argument("-o", "--offset", type=int, default=0)

    p = sub.add_parser("qid", help="full detail for one question id")
    p.add_argument("qid")

    p = sub.add_parser("search", help="full-text search over questions+options+answers+explanations")
    p.add_argument("terms", nargs="+")
    p.add_argument("-l", "--limit", type=int, default=20)

    p = sub.add_parser("audio", help="stats + samples of audio-flagged questions")
    p.add_argument("-l", "--limit", type=int, default=10)

    args = ap.parse_args(argv)
    db = connect()
    try:
        if args.cmd == "stats":
            cmd_stats(db)
        elif args.cmd == "exam":
            cmd_exam(db, args.key, args.limit)
        elif args.cmd == "exam-questions":
            cmd_exam_questions(db, args.exam_id, args.limit, args.offset)
        elif args.cmd == "qid":
            cmd_qid(db, args.qid)
        elif args.cmd == "search":
            cmd_search(db, args.terms, args.limit)
        elif args.cmd == "audio":
            cmd_audio(db, args.limit)
    finally:
        db.close()


if __name__ == "__main__":
    main()