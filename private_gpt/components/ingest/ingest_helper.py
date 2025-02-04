import logging
import zipfile
from pathlib import Path

from llama_index import Document
from llama_index.readers import JSONReader, StringIterableReader
from llama_index.readers.file.base import DEFAULT_FILE_READER_CLS

logger = logging.getLogger(__name__)

# Patching the default file reader to support other file types
FILE_READER_CLS = DEFAULT_FILE_READER_CLS.copy()
FILE_READER_CLS.update(
    {
        ".json": JSONReader,
        ".tex": StringIterableReader,
        ".txt": StringIterableReader,
        ".md": StringIterableReader,
        ".markdown": StringIterableReader,
        ".html": StringIterableReader,
    }
)


class IngestionHelper:
    """Helper class to transform a file into a list of documents.

    This class should be used to transform a file into a list of documents.
    These methods are thread-safe (and multiprocessing-safe).
    """

    @staticmethod
    def transform_file_into_documents(
        file_name: str, file_data: Path
    ) -> list[Document]:
        try:
            documents = IngestionHelper._load_file_to_documents(file_name, file_data)
            for document in documents:
                document.metadata["file_name"] = file_name
        except zipfile.BadZipFile:
            logger.warn(
                "Couldn't convert %s to text; skipping. Is this an encrypted Office file?",
                file_name
            )
            return []
        IngestionHelper._exclude_metadata(documents)
        return documents

    @staticmethod
    def _load_file_to_documents(file_name: str, file_data: Path) -> list[Document]:
        logger.debug("Transforming file_name=%s into documents", file_name)
        extension = Path(file_name).suffix
        reader_cls = FILE_READER_CLS.get(extension)

        if reader_cls is None:
            logger.warn(
                "No reader found for extension=%s, skipping file %s",
                extension,
                file_name,
            )
            return []

        logger.debug("Specific reader found for extension=%s", extension)
        if reader_cls is StringIterableReader:
            string_reader = reader_cls()
            return string_reader.load_data([file_data.read_text()])
        else:
            return reader_cls().load_data(file_data)

    @staticmethod
    def _exclude_metadata(documents: list[Document]) -> None:
        logger.debug("Excluding metadata from count=%s documents", len(documents))
        for document in documents:
            document.metadata["doc_id"] = document.doc_id
            # We don't want the Embeddings search to receive this metadata
            document.excluded_embed_metadata_keys = ["doc_id"]
            # We don't want the LLM to receive these metadata in the context
            document.excluded_llm_metadata_keys = ["file_name", "doc_id", "page_label"]
