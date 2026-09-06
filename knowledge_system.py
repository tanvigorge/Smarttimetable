import re
from collections import defaultdict


class TopicKnowledgeSystem:
    """Simple knowledge system for organizing study documents and answering topic questions."""

    def __init__(self, documents=None):
        self.documents = documents or []

    def organize_documents(self):
        grouped = defaultdict(lambda: defaultdict(list))
        for document in self.documents:
            subject = document.get("subject", "General")
            chapter = document.get("chapter", "General")
            grouped[subject][chapter].append(document)
        return {subject: {chapter: items for chapter, items in sorted(chapters.items())} for subject, chapters in sorted(grouped.items())}

    def get_coverage_counts(self):
        coverage = {}
        for subject, chapters in self.organize_documents().items():
            coverage[subject] = {chapter: len(items) for chapter, items in chapters.items()}
        return coverage

    def _extract_keywords(self, question):
        words = re.findall(r"[a-zA-Z]+", question.lower())
        return [word for word in words if len(word) > 3 and word not in {"what", "when", "where", "how", "why", "this", "that", "with", "from", "into", "them", "your"}]

    def _score_document(self, document, keywords):
        content = f"{document.get('title', '')} {document.get('content', '')}".lower()
        score = 0
        for keyword in keywords:
            if keyword in content:
                score += 1
        return score

    def _find_relevant_documents(self, query, limit=3):
        keywords = self._extract_keywords(query)
        if not keywords:
            keywords = ["topic"]

        scored_documents = []
        for document in self.documents:
            score = self._score_document(document, keywords)
            if score > 0:
                scored_documents.append((score, document))

        scored_documents.sort(key=lambda item: item[0], reverse=True)
        matched_documents = [document for _, document in scored_documents[:limit]]

        if len(matched_documents) < 2:
            top_document = scored_documents[0][1] if scored_documents else None
            if top_document is not None:
                subject = top_document.get("subject", "General")
                chapter = top_document.get("chapter", "General")
                for document in self.documents:
                    if document not in matched_documents and (document.get("subject") == subject or document.get("chapter") == chapter):
                        matched_documents.append(document)
                    if len(matched_documents) >= limit:
                        break

        return matched_documents

    def _build_references(self, documents):
        references = []
        for document in documents:
            references.append(
                {
                    "subject": document.get("subject", "General"),
                    "chapter": document.get("chapter", "General"),
                    "title": document.get("title", "Untitled"),
                }
            )
        return references

    def explain_topic(self, topic, level="beginner"):
        documents = self._find_relevant_documents(topic, limit=3)
        if not documents:
            return {
                "topic": topic,
                "explanation": "I could not find enough study material for this topic.",
                "references": [],
                "level": level,
            }

        explanation_parts = []
        for document in documents:
            explanation_parts.append(f"{document.get('title', 'Topic')}: {document.get('content', '')}")

        if len(documents) < 2:
            documents = self._find_relevant_documents(topic, limit=5)

        if level == "advanced":
            base_explanation = "Advanced view: " + " ".join(explanation_parts)
        elif level == "intermediate":
            base_explanation = "Intermediate view: " + " ".join(explanation_parts)
        else:
            base_explanation = "Beginner view: " + " ".join(explanation_parts)

        return {
            "topic": topic,
            "explanation": base_explanation,
            "references": self._build_references(documents),
            "level": level,
        }

    def synthesize_content(self, topic):
        documents = self._find_relevant_documents(topic, limit=3)
        if not documents:
            return {
                "topic": topic,
                "summary": "No supporting content was found.",
                "references": [],
            }

        summary = " ".join(document.get("content", "") for document in documents)
        return {
            "topic": topic,
            "summary": summary,
            "references": self._build_references(documents),
        }

    def solve_question(self, question):
        documents = self._find_relevant_documents(question, limit=3)
        if not documents:
            return {
                "question": question,
                "answer": "I could not find a matching topic in the available documents.",
                "references": [],
            }

        answer_parts = [document.get("content", "") for document in documents]
        return {
            "question": question,
            "answer": " ".join(answer_parts),
            "references": self._build_references(documents),
        }

    def generate_question_bank(self, topic, count=3):
        documents = self._find_relevant_documents(topic, limit=3)
        questions = []
        for index, document in enumerate(documents):
            if index == 0:
                questions.append(f"What is the main idea behind {document.get('title', 'this topic')}?")
            elif index == 1:
                questions.append(f"How does {document.get('title', 'this topic')} connect to the broader chapter?")
            else:
                questions.append(f"Why does {document.get('title', 'this topic')} matter?")
            if len(questions) >= count:
                break

        while len(questions) < count:
            questions.append(f"What would you like to review next about {topic}?")
        return questions[:count]

    def build_learning_progression(self, topic):
        return [
            {"stage": "theory", "title": f"Learn the core ideas of {topic}", "description": "Start with the main concepts from the available documents."},
            {"stage": "examples", "title": f"Study examples for {topic}", "description": "Review the related materials that show how the topic is applied."},
            {"stage": "practice", "title": f"Practice questions for {topic}", "description": "Use the generated question bank to test your understanding."},
            {"stage": "assessment", "title": f"Assess your understanding of {topic}", "description": "Check the references and summary to confirm complete topic coverage."},
        ]

    def identify_prerequisites(self, topic):
        documents = self._find_relevant_documents(topic, limit=3)
        prerequisites = []
        for document in documents:
            subject = document.get("subject", "General")
            chapter = document.get("chapter", "General")
            prerequisites.append(f"{subject} / {chapter}")
        if not prerequisites:
            prerequisites.append("General background")
        return prerequisites

    def map_topic_to_questions(self, topic):
        documents = self._find_relevant_documents(topic, limit=3)
        questions = []
        for document in documents:
            questions.append(f"What is the role of {document.get('title', topic)} in this topic?")
        if not questions:
            questions.append(f"What would you like to learn about {topic}?")
        return questions

    def build_knowledge_graph(self):
        graph = {}
        for document in self.documents:
            subject = document.get("subject", "General")
            chapter = document.get("chapter", "General")
            graph.setdefault(subject, {}).setdefault(chapter, []).append(document.get("title", "Untitled"))
        return graph

    def get_learning_analytics(self, topic):
        docs = self._find_relevant_documents(topic, limit=3)
        return {
            "topic": topic,
            "document_count": len(docs),
            "coverage": self.get_coverage_counts(),
            "prerequisites": self.identify_prerequisites(topic),
        }

    def answer_question(self, question):
        solved = self.solve_question(question)
        keywords = self._extract_keywords(question)
        related_questions = []
        for keyword in keywords[:3]:
            related_questions.append(f"What is the role of {keyword} in this topic?")

        explanation = self.explain_topic(question)
        return {
            "answer": solved["answer"],
            "references": solved["references"],
            "related_questions": related_questions,
            "coverage": self.get_coverage_counts(),
            "explanation": explanation["explanation"],
            "question_bank": self.generate_question_bank(question),
            "learning_progression": self.build_learning_progression(question),
            "prerequisites": self.identify_prerequisites(question),
            "topic_mapping": self.map_topic_to_questions(question),
            "knowledge_graph": self.build_knowledge_graph(),
            "analytics": self.get_learning_analytics(question),
        }
