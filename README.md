# Delay Prediction in Supply Chains: *A Hybrid Graph-Based and Machine Learning Approach*

[![DOI](https://zenodo.org/badge/1039110390.svg)](https://doi.org/10.5281/zenodo.18615068)

## Abstract

Global supply chains face frequent disruptions from both external events, such as natural disasters, and internal operational issues, including supplier and shipment delays. This work, carried out within the scope of the Horizon Europe project *Industrial Manufacturing As a sErvice STRategies and models for flexible, resilient, and reconfigurable value networks through Trusted and Transparent Operations* **M4ESTRO**, contributes to strengthening manufacturing resilience through real-time disruption monitoring, with a specific focus on internal delivery processes.

We present a mathematical framework for representing the delivery stages of supply chains, supported by lightweight predictive models built on a set of real-time indicators. These indicators quantify operational performance during dispatch and shipment processes, enabling the generation of reliable forecasts and associated uncertainty estimates. The framework leverages probabilistic methods and Markov chain based approaches to estimate delivery times, detect deviations from planned schedules and provide interpretable measures for operational decision-making.

A prototype implementation validates the approach by integrating heterogeneous data sources, including traffic conditions, weather information and supplier production calendars. Results show that monitoring delivery stages through indicators provides actionable insights and enables early disruption detection, offering a transparent and interpretable basis for strengthening resilience in internal operations.

## Thesis

Access the full thesis here: [**thesis**](thesis/sc-delay-prediction.pdf). 

## Repository Structure

- [**`code`**](code/) — Implementation and deployment code. See the [Code](#code) section for more details. 

- [**`data`**](data/) — Example input data and reference artifacts.

- [**`literature`**](literature/) — Collected literature and references.

- [**`plots`**](plots/) — Generated figures and visualizations from notebooks and evaluation scripts.

- [**`results`**](results/) — Versioned model outputs and evaluation artifacts.

- [**`thesis`**](thesis/) — Thesis-related materials.

## Code

The [**`code`**](code/) folder contains the main implementation of the research prototype, combining Python and TypeScript components, notebooks for experimentation and infrastructure definitions for deployment.

### Overview

- **Notebooks**: Top-level notebooks provide exploratory analyses, model evaluation and experiments on the defined indicators.

- [**`m4estro`**](code/m4estro): Main application bundle containing the Lambda functions and supporting modules.  

- [**`LambdaPY`/**](code/m4estro/LambdaPy): Python-based Lambda implementations. This is where the core model proposed in the thesis is implemented, including delay estimation, graph management, historical and real-time indicators implementation, and utility layers for statistics and platform integration.  

- [**`LambdaTS`/**](code/m4estro/LambdaTS): TypeScript-based Lambda functions for other system components, not part of the thesis. 

- [**`lib`/**](code/m4estro/lib): Infrastructure-as-code stacks defined using the AWS CDK, which configure and deploy the Lambda functions and associated cloud resources.  

- [**`bin`/**](code/m4estro/bin): Entry-point of the system.

- [**`params`**](code/params): Parameterized dashboard and configuration code, along with static assets for visualization.

## Acknowledgments

This work has received funding from the Horizon Europe research and innovation programme under grant agreement No.101138506.

<p align="center">
  <img src="assets/eu_funded.jpg" width="220"/>
</p>

## License

This repository is licensed under the [**Creative Commons Attribution 4.0 International (CC BY 4.0)**](https://creativecommons.org/licenses/by/4.0/legalcode). See the [LICENSE](LICENSE) file for the full text.