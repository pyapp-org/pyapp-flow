import csv
import logging
from pathlib import Path
from typing import Sequence, Tuple

import pyapp_flow as flow


@flow.step(name="Read books from file", output="books")
def read_books(*, library_path: Path) -> Sequence[Tuple[str, str]]:
    """
    Read book titles and ISBN from data file
    """
    data_file = library_path / "data.txt"
    with data_file.open() as f:
        reader = csv.reader(f)
        return list(reader)


@flow.step(name="Print books")
def print_book(*, book_title: str, book_isbn: str):
    """
    Print book title and ISBN
    """
    print(f"Title: {book_title}\nISBN:  {book_isbn}\n")


report_books_workflow = flow.Workflow(
    name="Read and print books",
    description="""
    Read books from the library path and print them out to the prompt.
    
    Requires the library_path to be set.
    """,
).nodes(
    read_books,
    flow.ForEach("book_title, book_isbn", in_var="books").loop(
        print_book,
    ),
)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    HERE = Path(__file__).parent
    report_books_workflow.execute(library_path=HERE)
