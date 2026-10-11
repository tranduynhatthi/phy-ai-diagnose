from pathlib import Path

p=Path('/app/app/main.py')
s=p.read_text(encoding='utf-8')
if 'FORCE_ADMIN_PASSWORD_RESET' not in s:
    if not s.startswith('import os'):
        s='import os\n'+s
    old='''            if not u:
                db.add(User(username=username.lower(), password_hash=hash_password(password), display_name=name, role=role))
            elif u.role != role:
                u.role = role'''
    new='''            if not u:
                db.add(User(username=username.lower(), password_hash=hash_password(password), display_name=name, role=role, is_active=True))
            else:
                if u.role != role:
                    u.role = role
                if role == "admin" and os.getenv("FORCE_ADMIN_PASSWORD_RESET","false").lower() == "true":
                    u.password_hash = hash_password(password)
                    u.is_active = True'''
    if old not in s:
        raise SystemExit('bootstrap account block not found')
    s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
