"""CLI: python run.py "your question" [--k 3] [--eval]"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rag import TfIdfIndex, answer, evaluate, load_docs

HERE = Path(__file__).parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("question", nargs="?", help="Question to answer")
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--eval", action="store_true")
    args = parser.parse_args()
    index = TfIdfIndex(load_docs(HERE / "docs.json"))
    if args.eval:
        print(json.dumps(evaluate(index, HERE / "eval.json", k=args.k),
                         indent=2))
        return
    if not args.question:
        parser.error("give a question, or use --eval")
    result = answer(index, args.question, k=args.k)
    if result["answer"] is None:
        print(result["refusal"])
    else:
        print("ANSWER (retrieved passage):")
        print(result["answer"])
        print("\nSOURCES:")
        for source in result["sources"]:
            print(f"  {source['doc_id']} {source['chunk_id']} score={source['score']}")


if __name__ == "__main__":
    main()
