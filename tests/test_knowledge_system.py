import unittest

from knowledge_system import TopicKnowledgeSystem


class TopicKnowledgeSystemTests(unittest.TestCase):
    def setUp(self):
        self.documents = [
            {
                "subject": "Biology",
                "chapter": "Cell Structure",
                "title": "Cells and Organelles",
                "content": "Cells contain organelles like mitochondria and ribosomes that help the cell function.",
            },
            {
                "subject": "Biology",
                "chapter": "Cell Structure",
                "title": "Mitochondria Basics",
                "content": "Mitochondria produce energy for the cell through respiration.",
            },
            {
                "subject": "Chemistry",
                "chapter": "Atoms",
                "title": "Atomic Structure",
                "content": "Atoms are made of protons, neutrons, and electrons.",
            },
        ]

    def test_organizes_documents_by_subject_and_chapter(self):
        system = TopicKnowledgeSystem(self.documents)
        grouped = system.organize_documents()

        self.assertIn("Biology", grouped)
        self.assertIn("Cell Structure", grouped["Biology"])
        self.assertEqual(len(grouped["Biology"]["Cell Structure"]), 2)

    def test_answers_related_questions_with_cross_document_references(self):
        system = TopicKnowledgeSystem(self.documents)
        result = system.answer_question("How do cells produce energy?")

        self.assertIn("energy", result["answer"].lower())
        self.assertGreaterEqual(len(result["references"]), 1)
        self.assertGreaterEqual(len(result["related_questions"]), 1)
        self.assertEqual(result["coverage"]["Biology"]["Cell Structure"], 2)

    def test_explains_topics_across_multiple_sources(self):
        system = TopicKnowledgeSystem(self.documents)
        explanation = system.explain_topic("cells")

        self.assertIn("explanation", explanation)
        self.assertGreaterEqual(len(explanation["references"]), 2)

    def test_generates_practice_questions_and_learning_progression(self):
        system = TopicKnowledgeSystem(self.documents)
        questions = system.generate_question_bank("cells")
        progression = system.build_learning_progression("cells")

        self.assertGreaterEqual(len(questions), 2)
        self.assertEqual(progression[0]["stage"], "theory")
        self.assertEqual(progression[-1]["stage"], "assessment")

    def test_supports_adaptive_explanations_and_prerequisites(self):
        system = TopicKnowledgeSystem(self.documents)
        beginner = system.explain_topic("cells", level="beginner")
        advanced = system.explain_topic("cells", level="advanced")
        prerequisites = system.identify_prerequisites("cells")

        self.assertIn("beginner", beginner["level"].lower())
        self.assertIn("advanced", advanced["level"].lower())
        self.assertGreaterEqual(len(prerequisites), 1)

    def test_builds_topic_mapping_and_knowledge_graph(self):
        system = TopicKnowledgeSystem(self.documents)
        mapping = system.map_topic_to_questions("cells")
        graph = system.build_knowledge_graph()

        self.assertGreaterEqual(len(mapping), 1)
        self.assertIn("Biology", graph)
        self.assertIn("Cell Structure", graph["Biology"])


if __name__ == "__main__":
    unittest.main()
