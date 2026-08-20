from app.services import slugify, services_to_list


def test_slugify():
    assert slugify("Bhuwan Pant") == "bhuwan-pant"
    assert slugify("Dr. Harish Rawat") == "dr-harish-rawat"


def test_services_to_list():
    assert services_to_list("Cloud\n\nDevOps\n AI ") == ["Cloud", "DevOps", "AI"]
