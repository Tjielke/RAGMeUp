from neo4j import GraphDatabase
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from typing import List

class Neo4jRetriever(BaseRetriever):
    def __init__(self, uri, user, password, k):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.k = k

    def close(self):
        self.driver.close()

    def add_documents(self, documents: List[Document]):
        with self.driver.session() as session:
            for doc in documents:
                session.run("""
                    MERGE (d:Document {hash: $hash})
                    SET d.content = $content,
                        d.metadata = $metadata
                """, hash=doc.metadata.get("id"), content=doc.page_content, metadata=doc.metadata)

    def _get_relevant_documents(self, query: str) -> List[Document]:
        with self.driver.session() as session:
            result = session.run("""
                MATCH (d:Document)
                WHERE d.content CONTAINS $query
                RETURN d.hash AS hash, d.content AS content, d.metadata AS metadata
                ORDER BY size(d.content) ASC
                LIMIT $k
            """, query=query, k=self.k)

            return [Document(page_content=record["content"], metadata=record["metadata"]) for record in result]

    def delete(self, ids: List[str]):
        with self.driver.session() as session:
            for doc_id in ids:
                session.run("MATCH (d:Document {hash: $hash}) DETACH DELETE d", hash=doc_id)
