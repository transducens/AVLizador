---
license: cc-by-4.0
task_categories:
- translation
---

## Subtask (CA-VA_Alignment) of Phrases adaptability task

This dataset was built from 200,000 sentences extracted from the Common Voice tool, an open resource that collects text contributions in various languages. These sentences were subjected to a rigorous filtering process, selecting only those with the greatest linguistic richness to ensure their usefulness in applications requiring language diversity and complexity.
Subsequently, the selected sentences were translated from Spanish to Catalan and Valencian. 

This translation process was carried out by an expert in Catalan philology, ensuring the linguistic quality and cultural accuracy of the translations in both languages. The expert intervention ensures that the translated sentences respect the dialectal and stylistic particularities of each variant of Catalan.
This dataset constitutes a valuable resource for natural language processing (NLP) projects focused on co-official languages of Spain, promoting linguistic diversity in technological applications. In this sense, it has been included in the Phrases task of Iberobench (a framework for evaluating language models of languages of the Iberian Peninsula).

### Dataset structure

The test set included in the Phrases task has 1,960 examples, with the following columns:
- id: A unique identifier for each phrase.
- ca: The Catalan translation of the original Spanish sentence in CommonVoice.
- va: The corresponding adaptation in Valencian.

## Dataset Creation

### Curation Rationale

This dataset is aimed at promoting the development of Machine Translation
between Valencian and Catalan, supporting research in multilingual NLP
and facilitating the development of translation systems for these language pairs.

### Source Data

The parallel data in this dataset is extracted from the [Common Voice tool](https://commonvoice.mozilla.org/es).

### Data Filtering and Normalization

A total of 200,000 Spanish sentences extracted from the Common Voice tool were subjected to a rigorous filtering process, selecting only those with the greatest linguistic richness to ensure their usefulness in applications requiring language diversity and complexity.
Subsequently, the selected sentences were translated from Spanish to Catalan and Valencian. 

This translation process was carried out by an expert in Catalan philology, ensuring the linguistic quality and cultural accuracy of the translations in both languages. 

## Funding

This dataset is funded by the *Ministerio para la Transformación Digital y de la Función Pública* — Funded by **EU – NextGenerationEU**, within the framework of the project *Desarrollo de Modelos ALIA*.

Additionally, this work has been funded by the VIVES: "Pla de Tecnologies de la Llengua per al valencià" project (2022/TL22/00215334) from the Projecte Estratègic per a la Recuperació i Transformació Econòmica (PERTE).

<!-- ## Acknowledgments

We extend our gratitude to all individuals and institutions that contributed to the development of this resource.

Special thanks to:

- [Data providers]  
- [Technological support providers]

We also acknowledge the financial, scientific, and technical contributions of the *Ministerio para la Transformación Digital y de la Función Pública – Funded by EU – NextGenerationEU* within the framework of the *Desarrollo de Modelos ALIA* project. -->


## Disclaimer

This dataset may contain biases or unintended artifacts.
Any third party using or deploying systems based on this dataset is solely responsible for ensuring compliant, safe, and ethical use, including adherence to relevant AI and data protection regulations.

The University of Alicante, as creator and owner of the dataset, assumes no liability for outcomes resulting from third-party use.

## License

This work is licensed under a [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/) licence.