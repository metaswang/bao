CN_SETTING = {
    "analysis": {
        "analyzer": {
            "default": {
                "tokenizer": "ik_smart",
                "char_filter": ["url_filter", "tsconvert", "periods_filter"],
                "filter": ["unique"],
            }
        },
        "tokenizer": {
            "tsconvert": {
                "type": "stconvert",
                "delimiter": "#",
                "keep_both": False,
                "convert_type": "t2s",
            }
        },
        "char_filter": {
            "tsconvert": {"type": "stconvert", "convert_type": "t2s"},
            "url_filter": {
                "type": "pattern_replace",
                "pattern": "http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
                "replacement": "",
            },
            "periods_filter": {
                "type": "pattern_replace",
                "pattern": "\\.",
                "replacement": "",
            },
        },
    },
    "similarity": {
        "custom_bm25": {
            "type": "BM25",
            "k1": 2.0,
            "b": 0.75,
        }
    },
}
