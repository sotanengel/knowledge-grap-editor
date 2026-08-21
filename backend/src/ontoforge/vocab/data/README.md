# Vendored vocabularies

These files are **verbatim copies** of published vocabularies, bundled so that
OntoForge works with no network access at all (NFR-06). They are third-party
artefacts: no formatter or hygiene hook touches them, so they stay byte-identical
to what their publishers serve.

| File | Vocabulary | Source | Licence |
|---|---|---|---|
| `rdf.ttl` | RDF | <https://www.w3.org/1999/02/22-rdf-syntax-ns.ttl> | W3C Software and Document Licence |
| `rdfs.ttl` | RDF Schema | <https://www.w3.org/2000/01/rdf-schema.ttl> | W3C Software and Document Licence |
| `owl.ttl` | OWL 2 | <https://www.w3.org/2002/07/owl.ttl> | W3C Software and Document Licence |
| `skos.rdf` | SKOS | <https://www.w3.org/2009/08/skos-reference/skos.rdf> | W3C Software and Document Licence |
| `dcterms.ttl` | DCMI Metadata Terms | <https://www.dublincore.org/specifications/dublin-core/dcmi-terms/dublin_core_terms.ttl> | CC BY 4.0 |
| `prov.ttl` | PROV-O | <https://www.w3.org/ns/prov-o.ttl> | W3C Software and Document Licence |
| `foaf.rdf` | FOAF | <http://xmlns.com/foaf/spec/index.rdf> | CC BY 1.0 |
| `schema.ttl` | schema.org | <https://schema.org/version/latest/schemaorg-current-https.ttl> | CC BY-SA 3.0 |

To refresh one, re-download it from the source above and leave it untouched
otherwise. `backend/src/ontoforge/vocab/loader.py` holds the matching metadata.
