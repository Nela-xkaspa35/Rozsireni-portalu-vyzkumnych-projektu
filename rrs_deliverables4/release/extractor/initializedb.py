#!/usr/bin/env python

from elasticsearch import Elasticsearch

HOST        = "localhost"
IDXPROJ     = "xdvora1f_projects"
IDXDELIV    = "xdvora1f_deliverables"
DOCTYPE     = "data"
PORT        = 9200

proj_settings = {
    # Custom case-insensitive analyzer for programme, subprogramme,
    # coordinator, participant, and country
    'analysis': {
        'analyzer': {
            'analyzer_keyword': {
                'tokenizer': 'keyword',
                'filter': 'lowercase'
            }
        }
    }
}

proj_mapping = {
    'data': {
        'properties': {
            "id":               {"type":"long"},
            "abbr":             {"type":"string"},
            "programme":        {"type":"string",   'analyzer'  : 'analyzer_keyword'},
            "subprogramme":     {"type":"string",   'analyzer'  : 'analyzer_keyword'},
            "year":             {"type":"string",   'index'     : 'not_analyzed'},
            "callForPropos":    {"type":"string"},
            "coordinator":      {"type":"string",   'analyzer'  : 'analyzer_keyword'},
            "coordAdd":         {"type":"string",   'analyzer'  : 'analyzer_keyword'},
            "coordFax":         {"type":"string",   'index'     : 'not_analyzed'},
            "country":          {"type":"string",   'analyzer'  : 'analyzer_keyword'},
            "coordName":        {"type":"string"},
            "coordTel":         {"type":"string"},
            "endDate":          {"type":"date",     "format"    : "dateOptionalTime"},
            "euCon":            {"type":"string"},
            "fundedUnder":      {"type":"string"},
            "fundingScheme":    {"type":"string"},
            "lastUpdate":       {"type":"date",     "format"    : "dateOptionalTime"},
            "objective":        {"type":"string"},
            "origWeb":          {"type":"string"},
            "delivWeb":         {"type":"string"},
            "participant":      {"type":"string",   'analyzer'  : 'analyzer_keyword'},
            "partCountry":      {"type":"string",   'analyzer'  : 'analyzer_keyword'},
            "projRef":          {"type":"string"},
            "startDate":        {"type":"date",     "format"    : "dateOptionalTime"},
            "subProg":          {"type":"string",   'index'     : 'not_analyzed'},
            "subjects":         {"type":"string",   'analyzer'  : 'analyzer_keyword'},
            "title":            {"type":"string"},
            "totalCost":        {"type":"string"},
            "url":              {"type":"string"},
            "ndelivs":          {"type":"integer"},
            "ndelivsok":        {"type":"integer"},
            "nextdelivs":       {"type":"integer"},
            "nextdelivsok":     {"type":"integer"},
            "isextracted":      {"type":"boolean"},
            "extraInfo":        {"type":"string"}
        }
    }
}

deliv_settings = {
    # Custom case-insensitive analyzer for programme, subprogramme,
    # coordinator, participant, and country
    'analysis': {
        'analyzer': {
            'analyzer_keyword': {
                'tokenizer': 'keyword',
                'filter': 'lowercase'
            }
        }
    }
}

deliv_mapping = {
    'data': {
        'properties': {
            "id":               {"type":"long"},
            "abbr":             {"type":"string"},
            "programme":        {"type":"string",   'analyzer'  : 'analyzer_keyword'},
            "subprogramme":     {"type":"string",   'analyzer'  : 'analyzer_keyword'},
            "year":             {"type":"string",   'index'     : 'not_analyzed'},
            "callForPropos":    {"type":"string"},
            "coordinator":      {"type":"string",   'analyzer'  : 'analyzer_keyword'},
            "coordAdd":         {"type":"string",   'analyzer'  : 'analyzer_keyword'},
            "coordFax":         {"type":"string",   'index'     : 'not_analyzed'},
            "country":          {"type":"string",   'analyzer'  : 'analyzer_keyword'},
            "coordName":        {"type":"string"},
            "coordTel":         {"type":"string"},
            "deliv_id":         {"type":"string"},
            "deliv_title":      {"type":"string"},
            "deliv_url":        {"type":"string"},
            "deliv_article":    {"type":"string"},
            "deliv_extraInfo":  {"type":"string"},
            "endDate":          {"type":"date",     "format"    : "dateOptionalTime"},
            "euCon":            {"type":"string"},
            "fundedUnder":      {"type":"string"},
            "fundingScheme":    {"type":"string"},
            "lastUpdate":       {"type":"date",     "format"    : "dateOptionalTime"},
            "objective":        {"type":"string"},
            "origWeb":          {"type":"string"},
            "delivWeb":         {"type":"string"},
            "participant":      {"type":"string",   'analyzer'  : 'analyzer_keyword'},
            "partCountry":      {"type":"string",   'analyzer'  : 'analyzer_keyword'},
            "projRef":          {"type":"string"},
            "startDate":        {"type":"date",     "format"    : "dateOptionalTime"},
            "subProg":          {"type":"string",   'index'     : 'not_analyzed'},
            "subjects":         {"type":"string",   'analyzer'  : 'analyzer_keyword'},
            "title":            {"type":"string"},
            "totalCost":        {"type":"string"},
            "url":              {"type":"string"},
            "ndelivs":          {"type":"integer"},
            "ndelivsok":        {"type":"integer"},
            "nextdelivs":       {"type":"integer"},
            "nextdelivsok":     {"type":"integer"},
            "isextracted":      {"type":"boolean"},
            "extraInfo":        {"type":"string"}
        }
    }
}

es = Elasticsearch(host=HOST, port=PORT)
es.indices.create(index=IDXPROJ,    body={'settings' : proj_settings,  'mappings': proj_mapping  })
es.indices.create(index=IDXDELIV,   body={'settings' : deliv_settings, 'mappings': deliv_mapping })

