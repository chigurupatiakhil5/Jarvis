import os

_OUTPUT_ROOT = "output"


def save_document(subfolder: str, filename: str, content: str) -> str:
    dir_path = os.path.join(_OUTPUT_ROOT, subfolder)
    os.makedirs(dir_path, exist_ok=True)

    file_path = os.path.join(dir_path, filename)
    with open(file_path, "w") as f:
        f.write(content)

    return file_path
