import sys, os, json

# workspace/skills/sakila-query/scripts/ → workspace/sakila_osm/
script_dir = os.path.dirname(os.path.abspath(__file__))
workspace_dir = os.path.normpath(os.path.join(script_dir, "..", "..", ".."))
sakila_osm_dir = os.path.join(workspace_dir, "sakila_osm")
sys.path.insert(0, sakila_osm_dir)

from compiler.compiler import SemanticCompiler

osm_path = os.path.join(sakila_osm_dir, "sakila_osm.yaml")
compiler = SemanticCompiler(osm_path)
meta = compiler.get_metadata()

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False)
print(json.dumps(meta, ensure_ascii=False, indent=2))
