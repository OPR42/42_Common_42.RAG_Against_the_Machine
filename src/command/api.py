from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from src.command.cli import CLI, CLIError

app = FastAPI(swagger_ui_parameters={"syntaxHighlight": False})
cli = CLI()


class SearchQuery(BaseModel):
    """Represent a search request received through the HTTP API."""
    query: str
    k: int = Field(default=5, ge=1)


@app.get("/")
async def root() -> dict[str, str]:
    """Return basic information about the API and its documentation."""
    return {
        "message": "RAG Against the Machine API",
        "documentation": "/docs",
    }


@app.post("/search", response_class=PlainTextResponse)
async def search(
        args: SearchQuery
        ) -> str | None:
    """
    Search the indexed corpus and return the retrieved context as plain text.
    """
    try:
        results = cli.search(query=args.query, k=args.k, basic_print=False,
                             tui_display=False, return_results=True)
        print(f"\33[0;35mSEARCH\33[0;97m:   \33[0;33m{args.query}\33[0m")
    except CLIError as e:
        raise HTTPException(400, str(e))
    if results is not None:
        print(f"\33[0;35mRESULTS\33[0;97m:\n\33[0;36m{results}\33[0m")
        return results
    return None


@app.post("/answer")
async def answer(args: SearchQuery) -> dict[str, Any]:
    """
    Generate an answer to a user query using retrieved context.
    """
    try:
        answer = cli.answer(query=args.query, k=args.k, basic_print=False,
                            tui_display=False, return_results=True)
        print(f"\33[0;35mREQUEST\33[0;97m:  \33[0;33m{args.query}\33[0m\n"
              f"\33[0;35mANSWER\33[0;97m:   \33[0;36m{answer}\33[0m")
    except CLIError as e:
        raise HTTPException(400, str(e))
    return {'response': answer}
