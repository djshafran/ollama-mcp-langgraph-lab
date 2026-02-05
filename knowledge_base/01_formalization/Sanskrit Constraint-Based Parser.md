# Sanskrit Constraint-Based Parser (University of Hyderabad – _Samsaadhanii_)

## Official Source and License

The University of Hyderabad’s Sanskrit Computational Linguistics group (led by Prof. Amba Kulkarni) provides a constraint-based Sanskrit parser as part of the _Samsaadhanii_ toolkit[[1]](https://www.sanskrit-trikashaivism.com/sanskrit-directory/detail/sanskrit-uohyd-ac-in-scl#:~:text=This%20site%20provides%20tools%20for,segmentation%2C%20sandhi%20splitter%2C%20and%20parsing). The latest implementation is openly available on their official GitHub repository under the GNU GPL license[[2]](https://github.com/samsaadhanii/scl/blob/master/README.md#:~:text=All%20the%20packages%20are%20available,GPL%20license%20with%20this%20package)[[3]](https://sanskrit.uohyd.ac.in/scl/#:~:text=). This means the parser is open-source (free to use and modify under GPL). The _Samsaadhanii_ suite has been actively developed and maintained by UoH, and the parser adheres to Pāṇini’s grammatical framework (using Sanskrit dependency relations, or _kāraka_ roles, defined by Pāṇini’s system).

## Installation and Build Options

You can obtain the parser by cloning the **Samsaadhanii** repository and building it from source, or by using a ready-made Docker image:

- **Docker Image:** The easiest route is the provided Docker container which comes with all dependencies. A pre-built Docker image (“samsaadhanii-container”) includes the parser and related tools, simplifying installation[[4]](https://github.com/samsaadhanii/scl#:~:text=Installation%20via%20Docker). Using Docker, you can pull the image and run it to start up the parser’s web service or CLI environment (instructions are in the repository). This avoids manually setting up the complex environment.
- **Building from Source:** For a manual installation on Linux, first ensure you have all prerequisites (see below). Then clone the GitHub repo and run the build scripts. For example:

```bash
git clone https://github.com/samsaadhanii/scl.git  
cd scl  
./configure  
make  
sudo make install  
```

This will compile and install the Sanskrit Computational Linguistics tools including the parser[[5]](https://github.com/samsaadhanii/scl/blob/master/README.md#:~:text=git%20clone%20https%3A%2F%2Fgithub). (There is also a configuration file spec.txt to set paths, as noted in the README.) After installation, the parser’s components (CGI scripts, binaries, etc.) will be set up – often under an Apache CGI directory if you follow the default installation.

## Input and Output Format

**Input:** The parser expects a Sanskrit sentence as input (in plain text). It supports Devanagari script input or various transliteration schemes (e.g. IAST, ITRANS, Harvard-Kyoto, SLP1, WX)[[6]](https://gist.github.com/hrishikeshrt/231e91dbc364b50916f1d465afee18bb#:~:text=self,self.status%20%3D). You may need to ensure the input is in _anvaya_ (prose word order) for best results, especially if parsing verses[[7]](https://www.academia.edu/84618487/Semantic_Annotation_and_Querying_Framework_based_on_Semi_structured_Ayurvedic_Text#:~:text=,prose%20form). The system can also handle Sandhi (euphonic combination) processing – you can either input a fully sandhi-joined sentence or split it beforehand. There are options to have the tool attempt sandhi-splitting as part of parsing if needed (e.g. a parameter for sandhi yes/no). Typically, the input is first run through the morphological analyzer to get all possible parses for each word.

**Output:** The output is a dependency parse of the sentence – essentially a parse tree indicating the grammatical relationships between words. The parser will identify roles like _kartṛ_ (agent/subject), _karman_ (object), _adhikaraṇa_ (locative adjunct), etc., for the words in the sentence[[8]](https://aclanthology.org/W19-7502.pdf#:~:text=a%204%200%20kart%E1%B9%9B%20d,edges%20and%20their%20compatible%20edges). Internally, it produces a set of dependency links which form a directed tree that satisfies all grammatical constraints (like expectancy and compatibility from Pāṇinian theory). In practice, you can obtain the results in multiple formats: for example, the web interface can display a graphical dependency tree (SVG image) and a tabular breakdown of the relations. The toolkit allows exporting the parse result in machine-readable formats such as JSON, CSV or TXT[[9]](https://hrishikeshrt.github.io/publication/wsc2023_1/slides.pdf#:~:text=,can%20be%20exported%20as%20PNG). The JSON output will list each word along with its morphological analysis and its relation to other words (head–dependent pairs with relation labels). There is also an HTML output (used by the e-reader interface) which shows the analyzed sentence with hyperlinks or pop-ups for the relations. If using the command-line, you may get output files like a table.csv (with morphological analyses of each word) and a graph.txt (listing dependency edges), which can be post-processed into a parse tree structure. In summary, **text in (Sanskrit sentence) -> parse tree out** (as a set of dependency relations, which can be visualized or output as structured data).

## Usage: CLI and API Access

**Command-line:** The parser can be invoked via command-line scripts after installation. The distribution is designed to run as a web service (CGI scripts), but you can also call its core logic directly. For example, the toolkit provides a Perl script (callmtshell.pl) which can be used to run the morphological analyzer and parser on an input string from the shell[[10]](https://gist.github.com/hrishikeshrt/231e91dbc364b50916f1d465afee18bb#:~:text=subprocess.run%28%5B%20f%27,scl_path%7D%2Fconverters%2Fconvert.pl). This script requires arguments such as the input text (in a chosen encoding), an indicator for using the full parser, text type (Prose/Śloka), etc., and it produces output files for the parse. In practice, one could write a shell or Python wrapper to call this script. Indeed, developers have created Python REPL wrappers for the Samsaadhanii parser that call these scripts under the hood and then parse the resulting files into Python data structures[[10]](https://gist.github.com/hrishikeshrt/231e91dbc364b50916f1d465afee18bb#:~:text=subprocess.run%28%5B%20f%27,scl_path%7D%2Fconverters%2Fconvert.pl)[[11]](https://gist.github.com/hrishikeshrt/231e91dbc364b50916f1d465afee18bb#:~:text=def%20do_view_analysis%28self%2C%20sent_id%29%3A%20,dumps%28analysis%2C%20ensure_ascii%3DFalse%2C%20indent%3D2%29%29%20print). In other words, while there isn’t an official one-call Python API, you _can_ call the parser from Python by invoking the installed CLI tools (e.g. via subprocess) and then reading the output. The parsing process might be a bit heavy, so expect that calling it will generate a temporary directory of results (including an SVG image of the tree, error logs, etc.). If you prefer not to manage files, you could run the parser in a local server mode: for instance, run an Apache server with the CGI scripts or use the Docker container’s web API.

**Web API:** The University’s server provides HTTP endpoints (CGI-based) for many tools. For example, there is an API for the morphological analyzer and even an integrated one for the parser via the _Anusāraka_ interface[[12]](https://sanskrit.uohyd.ac.in/scl/API_DOC/API_DOC.pdf#:~:text=encoding%3DWX%26out_encoding%3DDevanagari%26splitter%3DNone%26parse%3DFULL%26tlang%3DHin%02di%26text_t%20ype%3DSloka%26compound_analysis%3DYES%26mode%3Djson%26text%3DrAmaH,their%20values). Using these, you can send an HTTP request with the Sanskrit text and parameters (like mode=json to get JSON output). In a local setup, after running the Apache CGI, you could similarly access http://localhost/cgi-bin/scl/… endpoints. This returns a JSON containing the full analysis (morphological segments, compound splits, and dependency links). This approach allows calling the parser from any language (including Python, via HTTP requests) without dealing with low-level file I/O.

**Example:** For instance, once installed, you might do something like:

- Command line usage:  
      
    ```bash
    echo "rAmaH vanam gacChati" | ./run_parser.sh --input_encoding=WX --text_type=Prose --parser=Full
    ```

(This is illustrative – actual script name and options may differ; in the repository the callmtshell.pl is used with several parameters as shown above.) This would output files or an HTML with Rama (rAmaH) as the subject (_kartṛ_) of the verb _gacChati_ (“goes”), and _vanam_ (“to the forest”) as the object or locative depending on context.

- Using the API (JSON mode): you could call a URL like .../cgi-bin/scl/MT/prog/morph/morph.cgi?word=rAmaH&...&mode=json for morphology, or the combined endpoint for parsing (the documentation shows an anusaaraka.cgi which performs full parsing and returns JSON[[12]](https://sanskrit.uohyd.ac.in/scl/API_DOC/API_DOC.pdf#:~:text=encoding%3DWX%26out_encoding%3DDevanagari%26splitter%3DNone%26parse%3DFULL%26tlang%3DHin%02di%26text_t%20ype%3DSloka%26compound_analysis%3DYES%26mode%3Djson%26text%3DrAmaH,their%20values)). The JSON output would list each word, its lemma and features, and a list of relations (e.g., "relation": "kartR", "src": "rAmaH", "dst": "gacChati" indicating Rama is the agent of “goes”).

In summary, **you can run the parser either as a web service or via command-line scripts.** With some scripting, it is feasible to integrate it into a Python pipeline (either by local subprocess calls to the CLI as shown, or by running a local server and querying it). The official distribution doesn’t ship a one-click Python library, but the functionality is accessible programmatically.

## Dependencies and Requirements

Because this system implements a full Sanskrit grammatical analyzer, the setup is fairly complex. Key dependencies and environment requirements include:

·       **System/Build Tools:** GNU build tools (GCC, G++, Make), Flex (lexical analyzer generator), Bison (parser generator), and Graphviz (used to draw dependency trees)[[13]](https://github.com/samsaadhanii/scl#:~:text=,make). These are needed to compile the code and produce parse graphs.

·       **Web/CGI:** Apache HTTP Server with CGI enabled (if you plan to use the web interface)[[14]](https://github.com/samsaadhanii/scl#:~:text=1.%20Pre). The parser’s interface is originally designed as CGI scripts, so having Apache is recommended for full functionality (though not strictly required if calling from CLI only).

·       **Programming Languages:** _OCaml_ (with camlp4 pre-processor) is required to build certain components[[15]](https://github.com/samsaadhanii/scl#:~:text=2). In fact, the installation notes specify a particular OCaml version (e.g. 4.08) and the need to patch camlp4, because part of the lexical/morphological engine (the “Zen” library from INRIA) is in OCaml. Also, Java (a JDK) is listed as a requirement[[16]](https://github.com/samsaadhanii/scl#:~:text=,jdk%20%2A%20timeout), likely for some ancillary tools or the GUI. _Perl_ and _Python_ are used for various scripts (the glue scripts and some data processing).

·       **Python Libraries:** If you install manually, you’ll need a few Python3 packages for data handling: _pandas_, _openpyxl_, _anytree_, and devtrans (possibly a transliteration utility)[[17]](https://github.com/samsaadhanii/scl#:~:text=%2A%20default,Ocaml%2C%20Ocamlp4%20patch). These are used for things like output formatting or transliteration conversions.

·       **Other Linguistic Resources:** The tool uses large lexical databases. It integrates UoH’s own lexicon and also can interface with Gérard Huet’s Sanskrit Heritage Engine (there is mention of cloning a Zen repository and choosing between “UoHyd” vs “GH” morphological analyzers)[[18]](https://gist.github.com/hrishikeshrt/231e91dbc364b50916f1d465afee18bb#:~:text=%27DEV%27%2C%20,Prose%27%2C%20%27Sloka%27%2C%20%27Vedic). By default, the full installation will pull in those resources. Ensure you have _lttoolbox_ (an Apertium library for finite-state morphology) installed as noted[[19]](https://github.com/samsaadhanii/scl#:~:text=,python).

·       **Hardware/Runtime:** There are no hard-coded limits documented, but parsing Sanskrit can be computationally intensive. The algorithm tries to resolve all possible relations and then constraints, which can grow exponentially with sentence length. In practice, normal sentences parse in a few seconds, but very long or ambiguous sentences (especially poetry with many permutations) might be slow. Ensure you have a decent amount of RAM and CPU if parsing heavy inputs. Also, the code uses a timeout utility[[16]](https://github.com/samsaadhanii/scl#:~:text=,jdk%20%2A%20timeout) – likely to avoid hanging on extremely complex inputs by capping parse time.

In summary, the UoH _Samsaadhanii_ parser is a comprehensive, Panini-style Sanskrit parsing system. It is **open-source (GPL)** and the official code can be obtained from UoH’s site or GitHub[[2]](https://github.com/samsaadhanii/scl/blob/master/README.md#:~:text=All%20the%20packages%20are%20available,GPL%20license%20with%20this%20package). Installation can be non-trivial due to many dependencies, but a Docker image is available for convenience[[4]](https://github.com/samsaadhanii/scl#:~:text=Installation%20via%20Docker). Once set up, you can feed in Sanskrit text (in Devanagari or transliteration) and get out a full morphological and dependency analysis – essentially a parse tree identifying how the words relate grammatically[[9]](https://hrishikeshrt.github.io/publication/wsc2023_1/slides.pdf#:~:text=,can%20be%20exported%20as%20PNG)[[8]](https://aclanthology.org/W19-7502.pdf#:~:text=a%204%200%20kart%E1%B9%9B%20d,edges%20and%20their%20compatible%20edges). The parser can be invoked via command-line or used through a web API, making it possible to integrate into a larger pipeline (with a bit of scripting to handle the input/output format)[[10]](https://gist.github.com/hrishikeshrt/231e91dbc364b50916f1d465afee18bb#:~:text=subprocess.run%28%5B%20f%27,scl_path%7D%2Fconverters%2Fconvert.pl)[[11]](https://gist.github.com/hrishikeshrt/231e91dbc364b50916f1d465afee18bb#:~:text=def%20do_view_analysis%28self%2C%20sent_id%29%3A%20,dumps%28analysis%2C%20ensure_ascii%3DFalse%2C%20indent%3D2%29%29%20print). This makes it suitable for use as the **L0 symbolic pipeline** component for Sanskrit, providing rich morphological and syntactic analysis grounded in Pāṇinian grammar.

**Sources:** The official _Samsaadhanii_ code and documentation[[1]](https://www.sanskrit-trikashaivism.com/sanskrit-directory/detail/sanskrit-uohyd-ac-in-scl#:~:text=This%20site%20provides%20tools%20for,segmentation%2C%20sandhi%20splitter%2C%20and%20parsing)[[5]](https://github.com/samsaadhanii/scl/blob/master/README.md#:~:text=git%20clone%20https%3A%2F%2Fgithub)[[2]](https://github.com/samsaadhanii/scl/blob/master/README.md#:~:text=All%20the%20packages%20are%20available,GPL%20license%20with%20this%20package)[[4]](https://github.com/samsaadhanii/scl#:~:text=Installation%20via%20Docker)[[9]](https://hrishikeshrt.github.io/publication/wsc2023_1/slides.pdf#:~:text=,can%20be%20exported%20as%20PNG)[[8]](https://aclanthology.org/W19-7502.pdf#:~:text=a%204%200%20kart%E1%B9%9B%20d,edges%20and%20their%20compatible%20edges)[[10]](https://gist.github.com/hrishikeshrt/231e91dbc364b50916f1d465afee18bb#:~:text=subprocess.run%28%5B%20f%27,scl_path%7D%2Fconverters%2Fconvert.pl) provide the details summarized above.

---

[[1]](https://www.sanskrit-trikashaivism.com/sanskrit-directory/detail/sanskrit-uohyd-ac-in-scl#:~:text=This%20site%20provides%20tools%20for,segmentation%2C%20sandhi%20splitter%2C%20and%20parsing) संसाधनी - A Sanskrit Computational Toolkit › Sanskrit Directory

[https://www.sanskrit-trikashaivism.com/sanskrit-directory/detail/sanskrit-uohyd-ac-in-scl](https://www.sanskrit-trikashaivism.com/sanskrit-directory/detail/sanskrit-uohyd-ac-in-scl)

[[2]](https://github.com/samsaadhanii/scl/blob/master/README.md#:~:text=All%20the%20packages%20are%20available,GPL%20license%20with%20this%20package) [[5]](https://github.com/samsaadhanii/scl/blob/master/README.md#:~:text=git%20clone%20https%3A%2F%2Fgithub) scl/README.md at master · samsaadhanii/scl · GitHub

[https://github.com/samsaadhanii/scl/blob/master/README.md](https://github.com/samsaadhanii/scl/blob/master/README.md)

[[3]](https://sanskrit.uohyd.ac.in/scl/#:~:text=)  संसाधनी

[https://sanskrit.uohyd.ac.in/scl/](https://sanskrit.uohyd.ac.in/scl/)

[[4]](https://github.com/samsaadhanii/scl#:~:text=Installation%20via%20Docker) [[13]](https://github.com/samsaadhanii/scl#:~:text=,make) [[14]](https://github.com/samsaadhanii/scl#:~:text=1.%20Pre) [[15]](https://github.com/samsaadhanii/scl#:~:text=2) [[16]](https://github.com/samsaadhanii/scl#:~:text=,jdk%20%2A%20timeout) [[17]](https://github.com/samsaadhanii/scl#:~:text=%2A%20default,Ocaml%2C%20Ocamlp4%20patch) [[19]](https://github.com/samsaadhanii/scl#:~:text=,python) GitHub - samsaadhanii/scl

[https://github.com/samsaadhanii/scl](https://github.com/samsaadhanii/scl)

[[6]](https://gist.github.com/hrishikeshrt/231e91dbc364b50916f1d465afee18bb#:~:text=self,self.status%20%3D) [[10]](https://gist.github.com/hrishikeshrt/231e91dbc364b50916f1d465afee18bb#:~:text=subprocess.run%28%5B%20f%27,scl_path%7D%2Fconverters%2Fconvert.pl) [[11]](https://gist.github.com/hrishikeshrt/231e91dbc364b50916f1d465afee18bb#:~:text=def%20do_view_analysis%28self%2C%20sent_id%29%3A%20,dumps%28analysis%2C%20ensure_ascii%3DFalse%2C%20indent%3D2%29%29%20print) [[18]](https://gist.github.com/hrishikeshrt/231e91dbc364b50916f1d465afee18bb#:~:text=%27DEV%27%2C%20,Prose%27%2C%20%27Sloka%27%2C%20%27Vedic) Running Samsaadhanii Parser From CLI · GitHub

[https://gist.github.com/hrishikeshrt/231e91dbc364b50916f1d465afee18bb](https://gist.github.com/hrishikeshrt/231e91dbc364b50916f1d465afee18bb)

[[7]](https://www.academia.edu/84618487/Semantic_Annotation_and_Querying_Framework_based_on_Semi_structured_Ayurvedic_Text#:~:text=,prose%20form) Semantic Annotation and Querying Framework based on Semi ...

[https://www.academia.edu/84618487/Semantic_Annotation_and_Querying_Framework_based_on_Semi_structured_Ayurvedic_Text](https://www.academia.edu/84618487/Semantic_Annotation_and_Querying_Framework_based_on_Semi_structured_Ayurvedic_Text)

[[8]](https://aclanthology.org/W19-7502.pdf#:~:text=a%204%200%20kart%E1%B9%9B%20d,edges%20and%20their%20compatible%20edges) aclanthology.org

[https://aclanthology.org/W19-7502.pdf](https://aclanthology.org/W19-7502.pdf)

[[9]](https://hrishikeshrt.github.io/publication/wsc2023_1/slides.pdf#:~:text=,can%20be%20exported%20as%20PNG) [PDF] Semantic Annotation and Querying Framework - Hrishikesh Terdalkar

[https://hrishikeshrt.github.io/publication/wsc2023_1/slides.pdf](https://hrishikeshrt.github.io/publication/wsc2023_1/slides.pdf)

[[12]](https://sanskrit.uohyd.ac.in/scl/API_DOC/API_DOC.pdf#:~:text=encoding%3DWX%26out_encoding%3DDevanagari%26splitter%3DNone%26parse%3DFULL%26tlang%3DHin%02di%26text_t%20ype%3DSloka%26compound_analysis%3DYES%26mode%3Djson%26text%3DrAmaH,their%20values) API_DOC

[https://sanskrit.uohyd.ac.in/scl/API_DOC/API_DOC.pdf](https://sanskrit.uohyd.ac.in/scl/API_DOC/API_DOC.pdf)