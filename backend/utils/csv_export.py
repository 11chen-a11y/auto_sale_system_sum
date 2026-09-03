# CSV 导出工具
# 生成带 UTF-8 BOM 的 CSV，Excel 可直接打开；日期、JSON 字段自动格式化

import csv
import io
import json
from datetime import date, datetime

from fastapi.responses import StreamingResponse


def _cell(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (datetime, date)):
        return str(value)
    return str(value)


def csv_response(rows, headers, filename):
    """rows: SQLAlchemy 模型对象列表；headers: [(中文列名, 字段名), ...]"""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([label for label, _ in headers])
    for row in rows:
        writer.writerow([_cell(getattr(row, key, None)) for _, key in headers])
    payload = ("\ufeff" + buffer.getvalue()).encode("utf-8")
    return StreamingResponse(
        iter([payload]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
