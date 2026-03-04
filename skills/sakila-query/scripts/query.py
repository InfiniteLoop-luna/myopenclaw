"""
query.py - IR → SQL 编译 + 执行

用法:
  python query.py <ir_json> [role]           # 编译 + 执行
  python query.py --compile-only <ir_json>   # 仅编译
  python query.py --metadata                 # 输出语义能力视图

数据库连接: 192.168.7.242 root/123456 sakila
"""
import sys
import os
import json

# workspace/skills/sakila-query/scripts/ → workspace/sakila_osm/
script_dir = os.path.dirname(os.path.abspath(__file__))
workspace_dir = os.path.normpath(os.path.join(script_dir, "..", "..", ".."))
sakila_osm_dir = os.path.join(workspace_dir, "sakila_osm")
sys.path.insert(0, sakila_osm_dir)

from compiler.compiler import SemanticCompiler

OSM_PATH = os.path.join(sakila_osm_dir, "sakila_osm.yaml")

DB_CONFIG = {
    "host": "192.168.7.242",
    "user": "root",
    "password": "123456",
    "database": "sakila",
    "charset": "utf8mb4",
}


def compile_ir(ir_json: str, role: str = "admin") -> dict:
    """编译 IR 为 SQL"""
    compiler = SemanticCompiler(OSM_PATH)
    ir_data = json.loads(ir_json)
    result = compiler.compile(ir_data, role=role)
    return {
        "success": result.success,
        "sql": result.sql,
        "errors": [{"code": e.code, "message": e.message, "field": e.field} for e in result.errors],
        "metadata": result.metadata,
    }


def execute_sql(sql: str, limit: int = 100) -> dict:
    """执行 SQL 并返回结果"""
    import pymysql
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor(pymysql.cursors.DictCursor)
        cur.execute(sql)
        rows = cur.fetchmany(limit)
        columns = [desc[0] for desc in cur.description] if cur.description else []
        row_count = cur.rowcount
        conn.close()
        # 处理 Decimal 等不可序列化类型
        clean_rows = []
        for row in rows:
            clean = {}
            for k, v in row.items():
                if hasattr(v, '__float__'):
                    clean[k] = float(v)
                else:
                    clean[k] = str(v) if v is not None else None
            clean_rows.append(clean)
        return {
            "success": True,
            "columns": columns,
            "rows": clean_rows,
            "row_count": row_count,
            "truncated": row_count > limit,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def compile_and_execute(ir_json: str, role: str = "admin", limit: int = 100) -> dict:
    """编译 IR 并执行 SQL"""
    result = compile_ir(ir_json, role)
    if not result["success"]:
        return result
    exec_result = execute_sql(result["sql"], limit)
    result["execution"] = exec_result
    return result


def get_metadata() -> dict:
    compiler = SemanticCompiler(OSM_PATH)
    return compiler.get_metadata()


if __name__ == "__main__":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False)

    if len(sys.argv) < 2 or sys.argv[1] == "--metadata":
        print(json.dumps(get_metadata(), ensure_ascii=False, indent=2))
        sys.exit(0)

    if sys.argv[1] == "--compile-only":
        ir_json = sys.argv[2]
        role = sys.argv[3] if len(sys.argv) > 3 else "admin"
        result = compile_ir(ir_json, role)
    else:
        ir_json = sys.argv[1]
        role = sys.argv[2] if len(sys.argv) > 2 else "admin"
        result = compile_and_execute(ir_json, role)

    print(json.dumps(result, ensure_ascii=False, indent=2))
