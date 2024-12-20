import os
from langchain.text_splitter import MarkdownHeaderTextSplitter
from text3 import text
import openai
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores.faiss import FAISS
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()
MODEL_GPT = os.getenv("MODEL_GPT")


client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
)


class Chunk:
    _database_initialized = False

    def __init__(self):
        if not Chunk._database_initialized:
            headers_to_split_on = [
                ("#", "Header 1"),
                ("##", "Header 2"),
                ("###", "Header 3"),
            ]

            markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
            chunks = markdown_splitter.split_text(text)

            embeddings = OpenAIEmbeddings()
            self.db = FAISS.from_documents(chunks, embeddings)
            Chunk._database_initialized = True

    async def async_get_answer(self, question: str = None):

        docs = self.db.similarity_search(question, k=2)

        chunks_for_content = [doc.page_content for i, doc in
                              enumerate(docs, start=1)]
        print('=================================================================================')
        for content in chunks_for_content:
            print(content)
            print('=================================================================================\n')

        result = openai.chat.completions.create(
            model=MODEL_GPT,
            messages=[
                {"role": "system", "content": "Ты нейропомощник 'Толя'! Отвечаешь уважительно сотрудникам компании на корпоративные вопросы!"},
                {"role": "user", "content": f" Отвечай подробно, но по заданному вопросу. Если информация описана по пунктам, предоставляй все пункты и ссылки! Не упоминай документ"
                                            f"в ответе. Документ с информацией для ответа клиенту: {''.join(chunks_for_content)} Вопрос: {question}"}
            ],
            temperature=0,
            n=1
        )
        answer = result.choices[0].message.content
        return answer
