from cqc_lem.run_content_plan import create_content
from cqc_lem.utilities.logger import myprint


def test_create_content():
    buyers_stages = [
        'awareness',
        #'consideration',
        #'decision'
    ]

    for stage in buyers_stages:
        content = create_content(1,"video", stage)
        myprint(f"""Content for {stage} stage: {content}""")

if __name__ == "__main__":
    test_create_content()