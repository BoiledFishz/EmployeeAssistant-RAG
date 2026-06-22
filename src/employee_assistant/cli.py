from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .graph import EmployeeAssistant


DEFAULT_HR_PATH = Path(__file__).resolve().parents[2] / "data" / "hr.txt"


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="企业雇员助手 RAG 原型")
    parser.add_argument(
        "--data",
        default=os.getenv("EMPLOYEE_ASSISTANT_DATA"),
        help="用于 RAG 的 UTF-8/GB18030 文本文档路径",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="忽略外部文档，使用内置演示政策",
    )
    return parser.parse_args()


def main() -> None:
    # Keep UTF-8 output predictable when the Windows terminal is configured for it.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = _arguments()
    source_path: str | None
    if args.demo:
        source_path = None
    elif args.data:
        source_path = args.data
    elif DEFAULT_HR_PATH.exists():
        source_path = str(DEFAULT_HR_PATH)
    else:
        print(
            "错误：未指定知识库。请使用 employee-assistant --data <hr.txt 路径>，"
            "或使用 --demo 运行内置样例。",
            file=sys.stderr,
        )
        raise SystemExit(2)

    try:
        assistant = EmployeeAssistant(source_path=source_path)
    except (FileNotFoundError, ValueError) as error:
        print(f"无法启动：{error}", file=sys.stderr)
        raise SystemExit(2) from error

    history: list[dict[str, str]] = []
    print("企业雇员助手（输入 exit 退出）")
    if source_path:
        print(f"当前 RAG 文档：{Path(source_path).resolve()}")
        print(f"已建立 {len(assistant.retriever.chunks)} 个检索块。")
    else:
        print("当前使用内置演示政策。")
    while True:
        question = input("\n你：").strip()
        if question.lower() in {"exit", "quit", "q"}:
            break
        result = assistant.ask(question, history=history)
        print(f"\n助手：{result['answer']}")
        if result.get("citations"):
            print("\n来源：")
            for citation in result["citations"]:
                print(
                    f"- [{citation['id']}] {citation['title']} / "
                    f"{citation['section']} ({citation['effective_date']})"
                )
        history.extend(
            [
                {"role": "user", "content": question},
                {"role": "assistant", "content": result["answer"]},
            ]
        )


if __name__ == "__main__":
    main()
