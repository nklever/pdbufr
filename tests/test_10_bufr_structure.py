import typing as T

import eccodes  # type: ignore

from pdbufr import bufr_filters, bufr_structure


def test_BufrKey() -> None:
    res = bufr_structure.BufrKey.from_level_key(0, "edition")

    assert res.level == 0
    assert res.rank == 0
    assert res.name == "edition"
    assert res.key == "edition"

    res = bufr_structure.BufrKey.from_level_key(0, "#1#temperature")

    assert res.level == 0
    assert res.rank == 1
    assert res.name == "temperature"
    assert res.key == "#1#temperature"


def test_message_structure() -> None:
    message: T.Mapping[str, T.Any] = {
        "edition": 1,
    }

    res = bufr_structure.message_structure(message)

    assert list(res) == [(0, "edition")]

    message = {
        "edition": 1,
        "#1#year": 2020,
        "#1#subsetNumber": 1,
        "#1#latitude": 43.0,
        "#1#temperature": 300.0,
        "#2#latitude": 42.0,
        "#2#temperature": 310.0,
        "#2#subsetNumber": 2,
        "#3#temperature": 300.0,
        "#1#latitude->code": "005002",
        "#2#latitude->code": "005002",
    }
    expected = [
        (0, "edition"),
        (0, "#1#year"),
        (0, "#1#subsetNumber"),
        (1, "#1#latitude"),
        (2, "#1#temperature"),
        (1, "#2#latitude"),
        (2, "#2#temperature"),
        (0, "#2#subsetNumber"),
        (1, "#3#temperature"),
    ]

    res = bufr_structure.message_structure(message)

    assert list(res)[:-2] == expected


def test_filtered_keys() -> None:
    message = {
        "edition": 1,
        "#1#year": 2020,
        "#1#subsetNumber": 1,
        "#1#latitude": 43.0,
        "#1#temperature": 300.0,
        "#2#latitude": 42.0,
        "#2#temperature": 310.0,
        "#2#subsetNumber": 2,
        "#3#temperature": 300.0,
        "#1#latitude->code": "005002",
        "#2#latitude->code": "005002",
    }
    expected = [
        (0, "edition"),
        (0, "#1#year"),
        (0, "#1#subsetNumber"),
        (1, "#1#latitude"),
        (2, "#1#temperature"),
        (1, "#2#latitude"),
        (2, "#2#temperature"),
        (0, "#2#subsetNumber"),
        (1, "#3#temperature"),
    ]
    expected_obj = [bufr_structure.BufrKey.from_level_key(*i) for i in expected]

    res = bufr_structure.filtered_keys(message)

    assert list(res)[:-2] == expected_obj

    res = bufr_structure.filtered_keys(message, include=("edition",))

    assert list(res) == [bufr_structure.BufrKey.from_level_key(0, "edition")]


def test_cached_filtered_keys() -> None:
    cache: T.Dict[T.Tuple[T.Hashable, ...], T.List[T.Any]] = {}
    message = {
        "edition": 3,
        "masterTableNumber": 0,
        "unexpandedDescriptors": [321212, 321213],
        "numberOfSubsets": 1,
    }
    expected = [
        (0, "edition"),
        (0, "masterTableNumber"),
        (0, "unexpandedDescriptors"),
        (0, "numberOfSubsets"),
    ]
    expected_obj = [bufr_structure.BufrKey.from_level_key(*i) for i in expected]

    res1 = bufr_structure.cached_filtered_keys(message, cache)

    assert len(cache) == 1
    assert res1 == expected_obj

    res2 = bufr_structure.cached_filtered_keys(message, cache)

    assert len(cache) == 1
    assert res1 is res2

    res = bufr_structure.cached_filtered_keys(message, cache, include=("edition",))

    assert len(cache) == 2
    assert res == [bufr_structure.BufrKey(0, 0, "edition")]

    message["unexpandedDescriptors"] = 321212

    res = bufr_structure.cached_filtered_keys(message, cache)

    assert len(cache) == 3
    assert res == expected_obj

    message["delayedDescriptorReplicationFactor"] = 1

    res = bufr_structure.cached_filtered_keys(message, cache)

    assert len(cache) == 4
    assert len(res) == 5


def test_extract_observations_simple() -> None:
    message = {
        "#1#pressure": 100,
        "#1#temperature": 300.0,
        "#2#pressure": 90,
        "#2#temperature": eccodes.CODES_MISSING_DOUBLE,
        "#1#pressure->code": "005002",
        "#2#pressure->code": "005002",
    }
    filtered_keys = list(bufr_structure.filtered_keys(message))[:-2]
    filters = {"pressure": bufr_filters.BufrFilter(slice(100))}
    expected = [
        {"pressure": 100, "temperature": 300.0},
        {"pressure": 90, "temperature": None},
    ]

    res = bufr_structure.extract_observations(message, filtered_keys, filters)

    assert list(res) == expected

    filters = {"pressure": bufr_filters.BufrFilter(slice(95, 100))}

    res = bufr_structure.extract_observations(message, filtered_keys, filters)

    assert list(res) == expected[:1]


def test_extract_observations_compelx() -> None:
    message = {
        "#1#latitude": 42,
        "#1#pressure": 100,
        "#1#temperature": 300.0,
        "#2#pressure": 90,
        "#2#temperature": eccodes.CODES_MISSING_DOUBLE,
        "#2#latitude": 43,
        "#3#temperature": 290.0,
        "#1#latitude->code": "005002",
        "#1#pressure->code": "005002",
        "#2#latitude->code": "005002",
        "#2#pressure->code": "005002",
    }
    filtered_keys = list(bufr_structure.filtered_keys(message))[:-2]
    filters = {"pressure": bufr_filters.BufrFilter(slice(100))}
    expected = [
        {"latitude": 42, "pressure": 100, "temperature": 300.0},
        {"latitude": 42, "pressure": 90, "temperature": None},
    ]

    res = bufr_structure.extract_observations(message, filtered_keys, filters)

    assert list(res) == expected

    filters = {"latitude": bufr_filters.BufrFilter(slice(None))}
    expected = [
        {"latitude": 42, "pressure": 100, "temperature": 300.0},
        {"latitude": 42, "pressure": 90, "temperature": None},
        {
            "latitude": 43,
            "temperature": 290.0,
            # these are an artifact of testing with dicts
            "latitude->code": "005002",
            "pressure->code": "005002",
        },
    ]

    res = bufr_structure.extract_observations(message, filtered_keys, filters)

    assert list(res) == expected
