import os
import re
import zipfile
import io
import tempfile
import subprocess
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml
import httpx
from sqlalchemy.orm import Session
from app.database import Skill

SKILLS_DIR = Path("./skills")

class SkillService:
    def __init__(self, storage_dir: Path = SKILLS_DIR):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def parse_skill_markdown(self, text: str, filename: str = "") -> Dict[str, Any]:
        text_clean = text.strip()
        name = ""
        description = ""
        body_content = text_clean

        # Check for YAML frontmatter
        if text_clean.startswith("---"):
            parts = text_clean.split("---", 2)
            if len(parts) >= 3:
                frontmatter_str = parts[1]
                body_content = parts[2].strip()
                try:
                    data = yaml.safe_load(frontmatter_str)
                    if isinstance(data, dict):
                        name = str(data.get("name") or data.get("title") or "").strip()
                        description = str(data.get("description") or data.get("summary") or "").strip()
                except Exception:
                    pass

        # If name not in frontmatter, find first H1 header
        if not name:
            h1_match = re.search(r'^\s*#\s+(.+)$', body_content, flags=re.MULTILINE)
            if h1_match:
                name = h1_match.group(1).strip()

        # If still no name, deduce from filename or folder path
        if not name and filename:
            p = Path(filename)
            stem = p.stem
            if stem.lower() in ["skill", "skills", "readme", "index"] and p.parent.name:
                name = p.parent.name.replace("_", " ").replace("-", " ").title()
            else:
                name = stem.replace("_", " ").replace("-", " ").title()

        if not name:
            name = "مهارت نام‌گذاری‌نشده"

        # If description not found, extract first paragraph under heading
        if not description:
            lines = [line.strip() for line in body_content.splitlines() if line.strip()]
            for line in lines:
                if not line.startswith("#") and len(line) > 10:
                    description = line[:200]
                    if len(line) > 200:
                        description += "..."
                    break

        return {
            "name": name,
            "description": description or "دستورالعمل و راهنمای تخصصی",
            "content": text_clean
        }

    def save_file_to_disk(self, rel_path: str, content: str) -> str:
        # Sanitize rel_path
        clean_rel = rel_path.replace("\\", "/").strip("/.")
        if not clean_rel:
            clean_rel = "skill.md"
        dest_path = self.storage_dir / clean_rel
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text(content, encoding="utf-8")
        return str(clean_rel)

    def import_single_skill(self, db: Session, content: str, filename: str, is_active: bool = True) -> Skill:
        parsed = self.parse_skill_markdown(content, filename)
        name = parsed["name"]
        description = parsed["description"]

        saved_path = self.save_file_to_disk(filename, content)

        # Check existing by name
        existing = db.query(Skill).filter(Skill.name == name).first()
        if existing:
            existing.description = description
            existing.content = content
            existing.filename = saved_path
            existing.is_active = is_active
            db.commit()
            db.refresh(existing)
            return existing
        else:
            new_skill = Skill(
                name=name,
                description=description,
                content=content,
                filename=saved_path,
                is_active=is_active
            )
            db.add(new_skill)
            db.commit()
            db.refresh(new_skill)
            return new_skill

    def scan_directory(self, dir_path_str: str, db: Session) -> Dict[str, Any]:
        p = Path(dir_path_str).resolve()
        if not p.exists():
            raise FileNotFoundError(f"مسیر مورد نظر یافت نشد: {dir_path_str}")
        if not p.is_dir():
            raise NotADirectoryError(f"مسیر مشخص شده یک پوشه نیست: {dir_path_str}")

        imported_count = 0
        skipped_count = 0
        skills_added = []
        errors = []

        # Find all .md files recursively
        for file_path in p.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in [".md", ".markdown"]:
                try:
                    rel_name = file_path.relative_to(p).as_posix()
                    content = file_path.read_text(encoding="utf-8", errors="replace")
                    if content.strip():
                        skill = self.import_single_skill(db, content, rel_name, is_active=True)
                        skills_added.append({
                            "id": skill.id,
                            "name": skill.name,
                            "filename": rel_name
                        })
                        imported_count += 1
                    else:
                        skipped_count += 1
                except Exception as e:
                    errors.append(f"خطا در پردازش {file_path.name}: {str(e)}")

        return {
            "total_found": imported_count + skipped_count,
            "imported": imported_count,
            "skipped": skipped_count,
            "skills": skills_added,
            "errors": errors
        }

    def import_zip_archive(self, zip_bytes: bytes, db: Session) -> Dict[str, Any]:
        imported_count = 0
        skills_added = []
        errors = []

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            for item in zf.infolist():
                if not item.is_dir() and item.filename.lower().endswith((".md", ".markdown")):
                    try:
                        with zf.open(item) as f:
                            raw = f.read()
                            content = raw.decode("utf-8", errors="replace")
                            if content.strip():
                                skill = self.import_single_skill(db, content, item.filename, is_active=True)
                                skills_added.append({
                                    "id": skill.id,
                                    "name": skill.name,
                                    "filename": item.filename
                                })
                                imported_count += 1
                    except Exception as e:
                        errors.append(f"خطا در فایل زیپ {item.filename}: {str(e)}")

        return {
            "imported": imported_count,
            "skills": skills_added,
            "errors": errors
        }

    def import_from_git_repo(
        self,
        repo_url: str,
        branch: Optional[str] = None,
        subpath: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Clone or download a Git/GitHub repository, detect all skill definitions (SKILL.md or .md files),
        parse frontmatter and instructions, bundle references, and register them into database and storage.
        """
        clean_url = repo_url.strip()
        if not clean_url:
            raise ValueError("آدرس مخزن گیت‌هاب نمی‌تواند خالی باشد.")

        # Extract repo name from URL
        clean_url_no_query = clean_url.split("?")[0].rstrip("/")
        parsed_url = urllib.parse.urlparse(clean_url_no_query)
        path_parts = [p for p in parsed_url.path.strip("/").split("/") if p]
        repo_name = "github_skill"
        if len(path_parts) >= 2:
            repo_name = path_parts[1].replace(".git", "")
        elif len(path_parts) == 1:
            repo_name = path_parts[0].replace(".git", "")

        # Support URLs containing /tree/<branch>/<subpath>
        detected_branch = branch
        detected_subpath = subpath
        if "/tree/" in clean_url_no_query:
            parts = clean_url_no_query.split("/tree/", 1)
            clean_url = parts[0]
            sub_parts = parts[1].split("/", 1)
            detected_branch = sub_parts[0]
            if len(sub_parts) > 1:
                detected_subpath = sub_parts[1]

        imported_skills = []
        errors = []

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            target_dir = temp_path / "repo"
            cloned = False

            # Method 1: Git CLI clone (--depth 1)
            git_cmd = ["git", "clone", "--depth", "1"]
            if detected_branch:
                git_cmd.extend(["--branch", detected_branch])
            git_cmd.extend([clean_url, str(target_dir)])

            try:
                res = subprocess.run(git_cmd, capture_output=True, text=True, timeout=60)
                if res.returncode == 0 and target_dir.exists():
                    cloned = True
                else:
                    errors.append(f"Git clone error: {res.stderr.strip()[:200]}")
            except Exception as e:
                errors.append(f"Git execution error: {str(e)}")

            # Method 2: Fallback to GitHub HTTP zip archive if clone failed
            if not cloned and "github.com" in clean_url:
                try:
                    owner = path_parts[0] if path_parts else "repo"
                    br = detected_branch or "main"
                    zip_url = f"https://github.com/{owner}/{repo_name}/archive/refs/heads/{br}.zip"
                    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                        resp = client.get(zip_url)
                        if resp.status_code == 200:
                            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                                zf.extractall(temp_path)
                            # Locate extracted inner directory
                            extracted_dirs = [d for d in temp_path.iterdir() if d.is_dir() and d != target_dir]
                            if extracted_dirs:
                                target_dir = extracted_dirs[0]
                                cloned = True
                except Exception as e:
                    errors.append(f"Zip fallback error: {str(e)}")

            if not cloned:
                raise RuntimeError(f"امکان دریافت مخزن از گیت‌هاب وجود ندارد. خطاها: {'; '.join(errors)}")

            # Focus on subpath if specified
            scan_root = target_dir
            if detected_subpath:
                candidate_sub = target_dir / detected_subpath
                if candidate_sub.exists() and candidate_sub.is_dir():
                    scan_root = candidate_sub

            # Scan for SKILL.md or .md files
            skill_files = list(scan_root.rglob("SKILL.md")) + list(scan_root.rglob("skill.md"))

            # If no dedicated SKILL.md found, check skills/ folder or all .md files
            if not skill_files:
                skills_folder = scan_root / "skills"
                if skills_folder.exists() and skills_folder.is_dir():
                    skill_files = [f for f in skills_folder.rglob("*.md") if f.is_file()]
                else:
                    skill_files = [
                        f for f in scan_root.rglob("*.md")
                        if f.is_file() and f.name.lower() not in [
                            "readme.md", "readme.en.md", "license.md",
                            "contributing.md", "attribution.md"
                        ]
                    ]

            # Fallback to README.md if no other markdown files exist
            if not skill_files:
                readme = scan_root / "README.md"
                if readme.exists():
                    skill_files = [readme]

            if not skill_files:
                raise FileNotFoundError("هیچ فایل مهارتی (مانند SKILL.md یا مستند markdown) در مخزن یافت نشد.")

            for sf in skill_files:
                try:
                    content = sf.read_text(encoding="utf-8", errors="replace")
                    if not content.strip():
                        continue

                    # If this skill has a companion 'reference' folder, append key reference tables
                    ref_dir = sf.parent / "reference"
                    if ref_dir.exists() and ref_dir.is_dir():
                        ref_texts = []
                        for rf in sorted(ref_dir.glob("*.md")):
                            r_content = rf.read_text(encoding="utf-8", errors="replace")
                            if r_content.strip():
                                ref_texts.append(f"\n\n---\n### 📚 پیوست مرجع: {rf.stem}\n{r_content.strip()}")
                        if ref_texts:
                            content += "".join(ref_texts)

                    # Build clean relative destination path
                    if sf.parent != scan_root and sf.parent != target_dir:
                        rel_filename = f"{repo_name}/{sf.parent.name}/{sf.name}"
                    else:
                        rel_filename = f"{repo_name}/{sf.name}"

                    skill = self.import_single_skill(db, content, rel_filename, is_active=True)
                    imported_skills.append({
                        "id": skill.id,
                        "name": skill.name,
                        "description": skill.description,
                        "filename": skill.filename
                    })
                except Exception as e:
                    errors.append(f"خطا در پردازش {sf.name}: {str(e)}")

        return {
            "repo_url": clean_url,
            "repo_name": repo_name,
            "imported_count": len(imported_skills),
            "skills": imported_skills,
            "errors": errors
        }

skill_service = SkillService()

