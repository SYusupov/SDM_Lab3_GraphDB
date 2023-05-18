import pandas as pd #for handling csv and csv contents
from rdflib import Graph, Literal, RDFS, RDF, URIRef, Namespace, Dataset #basic RDF handling
from rdflib.namespace import FOAF , XSD #most common namespaces
import urllib.parse #for parsing strings to URI's
from iribaker import to_iri
import math

def add_attribute(filename, g, predicate_name, property_type, subject_index=0, property_index=1):
    """Adding attribute from file"""
    df = pd.read_csv(filename)

    for _,row in df.iterrows():
        subject_value = row[subject_index]
        property_value = row[property_index]
        subject_n = URIRef(to_iri(data+subject_value))
        object_n = Literal(str(property_value), datatype=XSD[property_type])
        g.add((subject_n, VOCAB[predicate_name], object_n))
    
    return g

base_link = "http://www.gra.fo/schema/untitled-ekg#"

# name space for resources
# data = base_link+"/resource/"
data = base_link
DATA = Namespace(data)
# namespace for vocabulary
# vocab = base_link+'/vocab/'
vocab = base_link
VOCAB = Namespace(vocab)
# URI
# graph_uri = URIRef(data+'/examplegraph')
graph_uri = URIRef(base_link)

dataset = Dataset()
dataset.bind('g20data', DATA)
dataset.bind('g20vocab', VOCAB)

## load TBOX
g = dataset.graph(graph_uri)
dataset.default_context.parse('tbox.ttl', format='turtle')


## reading csv for conferences/journals
data_folder = "data/Processed_data/"
df = pd.read_csv(data_folder+"Conf_Jour_Area.csv")

jour_df = df.loc[df['Type']=='Journal']
conf_df = df.loc[df['Type']=='Conference']

for _,conf_r in jour_df.iterrows():
    # Journal
    conf = URIRef(to_iri(data+conf_r[0]))
    conf_name = Literal(conf_r[0], datatype=XSD['string'])

    g.add((conf, RDFS.label, conf_name))
    g.add((conf, RDF.type, VOCAB["Journal"]))

    # Journal - related_to -> Area
    for area in conf_r[-1].split(";"):
        area = area.strip()
        area_n = URIRef(to_iri(data+area))
        area_name = Literal(area, datatype=XSD['string'])

        g.add((area_n, RDFS.label, area_name))
        g.add((area_n, RDF.type, VOCAB["Area"]))
        g.add((conf, VOCAB['journal_related_to'], area_n))

for _,conf_r in conf_df.iterrows():
    # Conference
    conf = URIRef(to_iri(data+conf_r[0]))
    conf_name = Literal(conf_r[0], datatype=XSD['string'])

    g.add((conf, RDFS.label, conf_name))
    g.add((conf, RDF.type, VOCAB["Conference"]))

    # Conference - related_to -> Area
    for area in conf_r[-1].split(";"):
        area = area.strip()
        area_n = URIRef(to_iri(data+area))
        area_name = Literal(area, datatype=XSD['string'])

        g.add((area_n, RDFS.label, area_name))
        g.add((area_n, RDF.type, VOCAB["Area"]))
        g.add((conf, VOCAB['conference_related_to'], area_n))

## loading Papers
df1 = pd.read_csv(data_folder+'Redundant_Columns.csv') # another column we need
df = pd.read_csv(data_folder+"Cite_fake_New.csv")
df['Paper Year'] = df1['Year']

# putting the same names as in the schema
df['Paper Type'] = df['Paper Type'].replace({'Full Paper':'FullPaper', 'Short Paper': 'Shortpaper', 'Demo Paper':'Demopaper'})
df['Conference Type'] = df['Conference Type'].replace({"Regular Conference":"Regularconference", "Expert Group": "Expertgroup"})

reviews_df = pd.read_csv(data_folder+"review_New.csv")

for r_idx,row in df.iterrows():
    authors = [a.strip() for a in row[1].split(", ")]
    title, source_title, proceeding, volume = row[2:6]
    areas = [a.strip() for a in row[6].split(";")]
    cj_type = row[7]
    c_type = row[8]
    p_type = row[9]
    is_approved = True if row[10] == 'Yes' else False
    leader1 = row[11]
    leader2 = row[12]
    p_year = row[13]

    if p_type == 'Poster' and cj_type == 'Journal':
        raise Exception(f"Poster can be published to Journal at row {r_idx}")

    paper_n = URIRef(to_iri(data+title))
    title_n = Literal(title, datatype=XSD['string'])
    g.add((paper_n, RDFS.label, title_n))
    year_n = Literal(p_year, datatype=XSD.integer)
    g.add((paper_n, VOCAB['paperyear'], year_n))
    g.add((paper_n, RDF.type, VOCAB[p_type]))

    for author in authors:
        author_n = URIRef(to_iri(data+author))
        author_name_n = Literal(author, datatype=XSD['string'])
        g.add((author_n, RDFS.label, author_name_n))
        g.add((author_n, RDF.type, VOCAB["Author"]))
        g.add((author_n, VOCAB['writes'], paper_n))
    
    for area in areas:
        area_n = URIRef(to_iri(data+area))
        area_name = Literal(area, datatype=XSD['string'])
        g.add((area_n, RDFS.label, area_name))
        g.add((area_n, RDF.type, VOCAB["Area"]))
        g.add((paper_n, VOCAB['paper_related_to'], area_name))
    
    if cj_type == 'Conference':
        conf_n = URIRef(to_iri(data+source_title))
        g.add((paper_n, VOCAB['submitted_to_conference'], conf_n))
        g.add((conf_n, RDF.type, VOCAB[c_type]))
        
        if type(proceeding) != str:
            if is_approved:
                raise(KeyError("Proceeding not defined for an approved conference paper"))
        else:
            proceeding_n = URIRef(to_iri(data+proceeding))
            proceeding_name_n = Literal(proceeding, datatype=XSD.string)
            g.add((proceeding_n, RDFS.label, proceeding_name_n))
            g.add((proceeding_n, RDF.type, VOCAB["Proceeding"]))
            g.add((proceeding_n, VOCAB['belongs_to_conference'], conf_n))
            
            # Check if the Decision is Correctly Safed in the Dataset
            reviewers_decision = reviews_df.loc[reviews_df['Title']==title].Decision.value_counts().nlargest(1).index.to_list()[0]
            if reviewers_decision != is_approved:
                raise Exception(f"The decision is incorrectly written at row {r_idx}")
            
            if is_approved:
                g.add((paper_n, VOCAB['published_in_proceeding'], proceeding_n))
        
        chair_n = URIRef(to_iri(data+leader1))
        chair_name_n = Literal(leader1, datatype=XSD.string)
        g.add((chair_n, RDFS.label, chair_name_n))
        g.add((chair_n, RDF.type, VOCAB["Chair"]))
        g.add((conf_n, VOCAB['handled_by_chair'], chair_n))
        chair_n = URIRef(to_iri(data+leader2))
        chair_name_n = Literal(leader2, datatype=XSD.string)
        g.add((chair_n, RDFS.label, chair_name_n))
        g.add((chair_n, RDF.type, VOCAB["Chair"]))
        g.add((conf_n, VOCAB['handled_by_chair'], chair_n))

    elif cj_type == 'Journal':
        jour_n = URIRef(to_iri(data+source_title))
        g.add((paper_n, VOCAB['submitted_to_journal'], jour_n))
        
        if type(volume) != str:
            if is_approved:
                raise(KeyError("Volume not defined for an approved journal paper"))
        else:
            volume_n = URIRef(to_iri(data+volume))
            volume_name_n = Literal(volume, datatype=XSD.string)
            g.add((volume_n, RDFS.label, volume_name_n))
            g.add((volume_n, RDF.type, VOCAB["Volume"]))
            g.add((volume_n, VOCAB['belongs_to_journal'], jour_n))
            if is_approved:
                g.add((paper_n, VOCAB['published_in_volume'], volume_n))
        
        editor_n = URIRef(to_iri(data+leader1))
        editor_name_n = Literal(leader1, datatype=XSD.string)
        g.add((editor_n, RDFS.label, editor_name_n))
        g.add((editor_n, RDF.type, VOCAB["Editor"]))
        g.add((jour_n, VOCAB['handled_by_editor'], editor_n))
        editor_n = URIRef(to_iri(data+leader2))
        editor_name_n = Literal(leader2, datatype=XSD.string)
        g.add((editor_n, RDFS.label, editor_name_n))
        g.add((editor_n, RDF.type, VOCAB["Editor"]))
        g.add((jour_n, VOCAB['handled_by_editor'], editor_n))

df = pd.read_csv(data_folder+"review_New.csv")

for _,row in df.iterrows():
    title = row[6]
    decision = True if row[7]=='1' else False
    reviewer = row[9]
    review_text = row[10]
    assigned_by = row[11]
    is_conference = True if row[2] == 'Conference' else False

    paper_n = URIRef(to_iri(data+title))

    reviewer_n = URIRef(to_iri(data+reviewer))
    reviewer_name_n = Literal(reviewer, datatype=XSD['string'])
    g.add((reviewer_n, RDFS.label, reviewer_name_n))
    g.add((reviewer_n, RDF.type, VOCAB["Reviewer"]))
    
    decision_n = URIRef(to_iri(data+f"decision by {reviewer} for {title}"))
    decision_literal = Literal(f"decision by {reviewer} for {title}", datatype=XSD.string)
    g.add((decision_n, RDFS.label, decision_literal))
    g.add((decision_n, RDF.type, VOCAB["Decision"]))
    review_text_n = Literal(review_text, datatype=XSD.string)
    g.add((decision_n, VOCAB["review_text"], review_text_n))
    is_accepted_n = Literal(decision, datatype=XSD.boolean)
    g.add((decision_n, VOCAB["is_accepted"], is_accepted_n))

    leader_n = URIRef(to_iri(data+assigned_by))

    if is_conference:
        g.add((leader_n, VOCAB["chair_assigns"], reviewer_n))
    else:
        g.add((leader_n, VOCAB["editor_assigns"], reviewer_n))
    
    g.add((reviewer_n, VOCAB["submits"], decision_n))
    g.add((decision_n, VOCAB["about"], paper_n))

## Proceeding Npages
filename = "Proceeding_Mapping.csv"
predicate_name = "proceedingnpages"
property_type = "integer"

g = add_attribute(data_folder+filename, g, predicate_name, property_type)

## Volume Npages
filename = "Volume_Mapping.csv"
predicate_name = "volumenpages"
property_type = "integer"

g = add_attribute(data_folder+filename, g, predicate_name, property_type)

# Chair Age
filename = "Chair_Age.csv"
predicate_name = "chairage"
property_type = "integer"

g = add_attribute(data_folder+filename, g, predicate_name, property_type)

# Editor Age
filename = "Editor_Age.csv"
predicate_name = "editorage"
property_type = "integer"

g = add_attribute(data_folder+filename, g, predicate_name, property_type)

# Reviewer Age
filename = "Reviewer_Age.csv"
predicate_name = "reviewerage"
property_type = "integer"

g = add_attribute(data_folder+filename, g, predicate_name, property_type)

# Conf Starting year
filename = "Conf_Starting_Year.csv"
predicate_name = "conferencestartingyear"
property_type = "integer"

g = add_attribute(data_folder+filename, g, predicate_name, property_type)

# Jour Starting Year
filename = "Jour_Starting_Year.csv"
predicate_name = "jourstartingyear"
property_type = "integer"

g = add_attribute(data_folder+filename, g, predicate_name, property_type)

# Area ID
filename = "Area_ID.csv"
predicate_name = "areaid"
property_type = "integer"

g = add_attribute(data_folder+filename, g, predicate_name, property_type, subject_index=1, property_index=0)

# Author Affiliation
filename = "Affiliation_Mapping.csv"
predicate_name = "authoraffiliation"
property_type = "string"

g = add_attribute(data_folder+filename, g, predicate_name, property_type)

g.serialize(format='ttl', destination='abox.ttl')