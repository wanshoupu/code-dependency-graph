# dependency-graph

A lightweight python script to draw dependency diagrams of C++ classes that features
* Inheritance
* Composition
* Method references
* Distinguish classes, enums, and structs

# Quickstart
To use it follow the following steps

1. Install the required dependencies
```commandline
pip install -r requirements.txt
```
2. Run the command
```commandline
<path-to-repo>/dependency_graph.py <path-to-c++-folder> -o <output-folder>
```
3. Check the result

The program will write the following files in the `<output-folder>`
* `nodes.txt` lists all the nodes (classes, enums, structs)
* `edges.txt` lists all the edges (inheritance, composition, references)
* `graph.jpg` represents the dependency diagram in JEPG format for quick proofread
* `graph.pdf` represents the vector version of the same dependency diagram in PDF format

# Tips
Because the nondeterministic nature of `graphviz`, the rendering of the dependency diagram is 
not reproducible and may vary in quality. So one tip is to run the same program for multiple 
time and choose the best representation in graph. For example: 
```commandline
for i in {1..5}; do 2>&1 1>/dev/null <path-to-repo>/dependency_graph.py <path-to-c++-folder> -o 
<output-folder>-$i; done
```

## Manual

```
usage: dependency_graph.py input_dirs [-o output_dir]

positional arguments:
  folders                Path to one or more directories to scan for C++ source files

optional arguments:
  -o, --output          directory to contain the output files.
                        default: current directory
  -h, --help            show this help message and exit
```
