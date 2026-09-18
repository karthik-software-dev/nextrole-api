from sources.indeed_source import fetch_indeed_jobs
from processing.relevance import filter_relevant_jobs


def main():
    print("=" * 60)
    print("JOB DISCOVERY ENGINE - V3")
    print("=" * 60)

    print("\nFetching Indeed jobs through Apify...\n")

    jobs = fetch_indeed_jobs()

    print(f"Jobs received: {len(jobs)}")

    relevant_jobs = filter_relevant_jobs(jobs)

    print(f"Relevant backend jobs: {len(relevant_jobs)}\n")

    print("=" * 60)
    print("RELEVANT JOBS")
    print("=" * 60)

    for index, job in enumerate(relevant_jobs, start=1):
        print(f"\n#{index}")
        print(f"Title   : {job.get('positionName')}")
        print(f"Company : {job.get('company')}")
        print(f"Location: {job.get('location')}")
        print(f"Salary  : {job.get('salary')}")
        print(f"Score   : {job.get('relevanceScore')}")
        print(f"Apply   : {job.get('externalApplyLink')}")
        print(f"Indeed  : {job.get('url')}")

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()