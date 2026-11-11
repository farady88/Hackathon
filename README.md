## Lynceus - AI-Powered Project Discovery

# 1. Project Overview
Lynceus is an AI-powered search tool designed to help Accenture sales and delivery teams discover relevant previous projects using natural-language queries.

The tool aims to identify relevant project experience across different industries, technical terminology and languages, making it easier to find reusable solutions and capabilities from previous delivery work.


# 2. The Problem
Finding relevant examples of previous projects can be challenging because:

Project descriptions may use industry-specific terminology.

Similar solutions may be described differently across industries.

Project documentation may be written in different languages.

Important project information may be difficult to locate through traditional keyword searches.


# 3. Our Solution
Lynceus aims to address these challenges by:

 - Processing and enriching project documents into structured records.

 - Extracting key information such as industry, country, client problem, technology, scale and outcomes.

 - Allowing users to search using everyday natural language.

 - Returning ranked project matches with explanations of why they are relevant.

 - Providing traceable links to original project information.

 - Identifying when there is no strong match rather than returning irrelevant results.

# 4. Key Features

 - Natural-language search: Users can describe a client problem in plain English.

 - Cross-industry discovery: Finds relevant solutions even when different industries use different terminology.

 - Multilingual discovery: Supports retrieval of relevant projects written in other languages.

 - Structured project information: Organises project details into searchable fields.

 - Explainable results: Provides summaries and reasons for matching.

 - Source traceability: Links results back to their original documents.

# 5. Project Data & Enrichment

The solution uses a collection of historical project write-ups.

Each project is enriched with structured information, including:

 - Sector

 - Country

 - Client problem (plain English)

 - Capability or technique

 - Scale and outcome figures

 - Original document language

 - Potential reusability

AI-generated records are subject to human review, with original agent drafts and corrected versions retained.

# 6. How it works
1.) Project documents are loaded into the system.
2.) An AI agent extracts relevant information and creates structured records.
3.) Human reviewers check and correct selected records.
4.) A user enters a natural-language question.
5.) The search functionality retrieves and ranks relevant projects.
6.) Results are presented with summaries, matching explanations and source references.

# 7. Evaluation and Testing
The solution is evaluated using a test set of at least 10 questions, including:

 - General project searches.

 - Cross-industry terminology searches.

 - Non-English project searches.

 - Questions where no strong matching project exists.

Performance is assessed by checking whether the expected project appears within the top three search results.

# 8. Limitations & Improvements
Potential areas for improvement include:

 - Improving retrieval accuracy across more industries and languages.

 - Expanding the collection of searchable project records.

 - Improving the quality of AI-generated summaries.

 - Further validating results against original source documents.

 - Preparing the solution for deployment within an appropriate secure environment.

# 9. Tools and Languages used within the project
## AI Layer and RAG pipeline tools: 
VS Code
python
Anthropic SDK
Github
Git
Voyage AI
Chroma DB
Claude
Streamlit
FastAPI

## Search Engineer 
Python: Used to build the search engine, process project data, execute searches and return ranked results.
TF-IDF (Term Frequency–Inverse Document Frequency): Used to convert project descriptions and user queries into numerical vectors, assigning importance to words based on their frequency across the dataset.
Cosine Similarity: Used to compare the user's query vector against each project's vector, calculate similarity scores and rank projects from most to least relevant.

## Tools used for data pipeline:
Python: the language the pipeline is written in
json: saves the records and the issues as JSON files
pathlib: finds and reads the files and folders
langdetect: works out the language of each file
pytest: runs the tests on the loader


# 10. Team
Hackathon: Accenture x Sparta Global

Delivery Lead: Veerpal
Business Analysts: Noah and Hussein
Data Engineer: Dylan and Ayoola 
Search Engineer: Al-Ameen
Agent engineer: Faaruq 
Evaluation Lead: Inam
Evidence & Demo Lead: Hasan

Project: Lynceus
Date: 11 November 2026

# 11. Responsible Use of Data

Project information must be handled in accordance with the hackathon's data-handling requirements. AI-generated information must be reviewed by humans, and claims presented in search results must be traceable to their original sources.
