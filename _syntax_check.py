import py_compile, sys
files = [
  r"reports\utils\csv_export.py",
  r"reports\utils\xlsx_export.py",
  r"reports\views.py",
  r"reports\urls.py",
  r"bizsuite\urls.py",
]
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print("OK:", f)
    except py_compile.PyCompileError as e:
        print("SYNTAX ERROR in", f, "\n", e.msg)
        sys.exit(1)
print("All report files syntax OK")
