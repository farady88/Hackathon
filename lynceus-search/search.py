
# import json
# from pathlib import Path

# import pandas as pd
# from scipy.sparse import hstack
# from sklearn.feature_extraction.text import TfidfVectorizer
# from sklearn.metrics.pairwise import cosine_similarity


# # BASE_DIR = Path(__file__).resolve().parent
# # DATA_FILE = BASE_DIR / "mock_cases.json"
# # SOURCE_DIR = BASE_DIR / "mock_sources"


# BASE_DIR = Path(__file__).resolve().parent

# # Parent directory: Hackathon
# PROJECT_ROOT = BASE_DIR.parent

# # Actual project data
# DATA_FILE = PROJECT_ROOT / "data" / "records.json"

# # Original source documents
# SOURCE_DIR = PROJECT_ROOT / "corpus"


# # Starting feature weights
# WEIGHTS = {
#     "problem": 0.5,
#     "capability": 0.3,
#     "reusable": 0.2
# }


# # Loads the project data and builds the TF-IDF model
# def build_model():

#     with open(DATA_FILE, "r", encoding="utf-8") as file:
#         projects = json.load(file)

#     if not isinstance(projects, list) or not projects:
#         raise ValueError("The project JSON must be a non-empty list.")

#     df = pd.DataFrame(projects)

#     # Handles missing fields
#     for field in ["id", "summary", "source", *WEIGHTS]:
#         if field not in df.columns:
#             df[field] = ""

#         df[field] = df[field].fillna("").astype(str)

#     matrices = []
#     vectorizers = {}

#     # Converts each project feature into TF-IDF vectors
#     for field, weight in WEIGHTS.items():

#         vectorizer = TfidfVectorizer(stop_words="english")

#         try:
#             matrix = vectorizer.fit_transform(df[field])
#         except ValueError:
#             continue

#         matrices.append(matrix * weight)
#         vectorizers[field] = vectorizer

#     if not matrices:
#         raise ValueError("No searchable project descriptions found.")

#     # Combines the weighted features
#     X = hstack(matrices).tocsr()

#     return df, X, vectorizers


# # Finds the most relevant projects using cosine similarity
# def search_projects(df, X, vectorizers, query, k=3, min_score=0.15):

#     if not query.strip():
#         return []

#     # Converts the user's question into TF-IDF vectors
#     query_matrices = [
#         vectorizers[field].transform([query]) * WEIGHTS[field]
#         for field in vectorizers
#     ]

#     query_X = hstack(query_matrices).tocsr()

#     # Calculates cosine similarity and ranks projects
#     sims = cosine_similarity(query_X, X).ravel()
#     order = sims.argsort()[::-1]

#     results = []

#     for i in order:

#         # Ignores results below the provisional threshold
#         if sims[i] < min_score:
#             continue

#         # Identifies which fields share terms with the question
#         matches = []

#         for field, vectorizer in vectorizers.items():

#             analyzer = vectorizer.build_analyzer()

#             common = sorted(
#                 set(analyzer(query)) &
#                 set(analyzer(df.at[i, field]))
#             )

#             if common:
#                 matches.append(
#                     f"{field}: {', '.join(common[:5])}"
#                 )

#         # Locates the original source file
#         source_name = Path(df.at[i, "source"]).name
#         source_file = SOURCE_DIR / source_name

#         if source_file.is_file():
#             source = source_file.as_uri()
#         else:
#             source = f"{source_name} (file not linked yet)"

#         results.append({
#             "id": df.at[i, "id"],
#             "score": round(float(sims[i]), 3),
#             "summary": df.at[i, "summary"],
#             "why_matched": "; ".join(matches),
#             "source": source
#         })

#         if len(results) == k:
#             break

#     return results


# # Main program
# if __name__ == "__main__":

#     df, X, vectorizers = build_model()

#     question = input("Enter client problem: ")

#     results = search_projects(
#         df, X, vectorizers, question
#     )

#     if not results:
#         print("No strong match found.")

#     else:
#         for rank, project in enumerate(results, start=1):

#             print(f"\nResult {rank}: {project['id']}")
#             print(f"Similarity: {project['score']}")
#             print(f"Summary: {project['summary']}")
#             print(f"Why matched: {project['why_matched']}")
#             print(f"Source: {project['source']}")



import json
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

DATA_FILE = PROJECT_ROOT / "data" / "records.json"


# Gets the English text for searching
def get_search_text(record):

    english_text = str(record.get("text_english") or "").strip()

    if english_text:
        return english_text

    # Use original text only when it is already English
    language = str(record.get("language") or "").lower()

    if language in ("english", "en", "eng", "en-gb", "en-us"):
        return str(record.get("text_original") or "").strip()

    return ""


# Loads the projects and builds the TF-IDF model
def build_model():

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        projects = json.load(file)

    if not isinstance(projects, list) or not projects:
        raise ValueError("Expected a non-empty list of projects.")

    df = pd.DataFrame(projects)

    # Prepare the text used for searching
    df["search_text"] = df.apply(get_search_text, axis=1)

    if not df["search_text"].str.strip().any():
        raise ValueError("No English searchable text found.")

    # Convert project descriptions into TF-IDF vectors
    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2)
    )

    X = vectorizer.fit_transform(df["search_text"])

    # Keep the same return structure as our earlier code
    vectorizers = {"text": vectorizer}

    return df, X, vectorizers


# Searches and ranks the projects
def search_projects(df, X, vectorizers, query, k=3, min_score=0.15):

    if not query.strip():
        return []

    vectorizer = vectorizers["text"]

    # Convert the user's question into a TF-IDF vector
    query_X = vectorizer.transform([query])

    # Calculate cosine similarity
    sims = cosine_similarity(query_X, X).ravel()

    # Rank from highest to lowest
    order = sims.argsort()[::-1]

    results = []

    for i in order:

        if sims[i] < min_score:
            continue

        if not df.at[i, "search_text"].strip():
            continue

        # Identify overlapping search terms
        analyzer = vectorizer.build_analyzer()

        common = sorted(
            set(analyzer(query)) &
            set(analyzer(df.at[i, "search_text"]))
        )

        # Locate the original source document
        source_path = Path(str(df.at[i, "source_path"]))

        if not source_path.is_absolute():
            source_path = PROJECT_ROOT / source_path

        if source_path.is_file():
            source = source_path.resolve().as_uri()
        else:
            source = f"{source_path} (file not found)"

        results.append({
            "id": df.at[i, "case_id"],
            "score": round(float(sims[i]), 3),
            "why_matched": "Shared search terms: " + ", ".join(common[:8]),
            "source": source
        })

        if len(results) == k:
            break

    return results


# Main program
if __name__ == "__main__":

    df, X, vectorizers = build_model()

    print("Total records:", len(df))
    print("Searchable records:", (df["search_text"].str.len() > 0).sum())

    question = input("\nEnter client problem: ")

    # Request the top 3 results
    results = search_projects(
        df, X, vectorizers, question, k=3
    )

    if not results:
        print("\nNo strong match found.")

    else:
        print("\nTop 3 matching projects:")

        for rank, project in enumerate(results, start=1):
            print(f"\nRank {rank}: {project['id']}")
            print(f"Similarity: {project['score']}")
            print(f"Why matched: {project['why_matched']}")
            print(f"Source: {project['source']}")



# # Main program
# if __name__ == "__main__":

#     df, X, vectorizers = build_model()

#     print("Total records:", len(df))
#     print("Searchable records:", (df["search_text"].str.len() > 0).sum())

#     # Find records that cannot currently be searched
#     missing = df[df["search_text"].str.strip() == ""]

#     print("\nUnsearchable records:", len(missing))

#     for _, record in missing.iterrows():
#         print(
#             "Case:", record["case_id"],
#             "| Language:", record["language"],
#             "| English translation:",
#             bool(str(record.get("text_english") or "").strip()),
#             "| Original text:",
#             bool(str(record.get("text_original") or "").strip())
#         )

#     # Accept a user question
#     question = input("\nEnter client problem: ")

#     results = search_projects(df, X, vectorizers, question)

#     if not results:
#         print("\nNo strong match found.")

#     else:
#         for rank, project in enumerate(results, start=1):

#             print(f"\nResult {rank}: {project['id']}")
#             print(f"Similarity: {project['score']}")
#             print(f"Why matched: {project['why_matched']}")
#             print(f"Source: {project['source']}")



