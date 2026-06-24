"""数据完整性校验模块 - 被动记录，不主动扫描"""
import os, json, datetime

def _get_data_dir():
    from app.config import BASE_DIR
    return os.path.join(BASE_DIR, "Data")

ISSUES_FILE = None

def _ensure_issues_file():
    global ISSUES_FILE
    if ISSUES_FILE is None:
        ISSUES_FILE = os.path.join(_get_data_dir(), "system", "data_issues.json")
    return ISSUES_FILE

def _load_issues():
    f = _ensure_issues_file()
    if os.path.exists(f):
        with open(f, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return []

def _save_issues(issues):
    f = _ensure_issues_file()
    os.makedirs(os.path.dirname(f), exist_ok=True)
    with open(f, "w", encoding="utf-8") as fh:
        json.dump(issues, fh, ensure_ascii=False, indent=2)

def record_missing_file(file_path, product_id=0, product_name="系统文件", file_type="unknown"):
    """记录缺失文件，同一路径只记一次"""
    issues = _load_issues()
    existing = [i for i in issues if i["file_path"] == file_path and i["status"] == "open"]
    if existing:
        return
    issues.append({
        "id": f"mf_{hash(file_path) % 1000000}",
        "product_id": product_id,
        "product_name": product_name,
        "file_type": file_type,
        "file_path": file_path,
        "status": "open",
        "created_at": datetime.datetime.now().isoformat(),
    })
    _save_issues(issues)

def get_open_issues():
    issues = _load_issues()
    return [i for i in issues if i["status"] == "open"]

def resolve_issue(issue_id):
    issues = _load_issues()
    for i in issues:
        if i["id"] == issue_id:
            i["status"] = "resolved"
            i["resolved_at"] = datetime.datetime.now().isoformat()
            break
    _save_issues(issues)
    return len([i for i in issues if i["status"] == "open"])

def get_open_count():
    return len(get_open_issues())
