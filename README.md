# dependency-graph

A python script to show the "include" dependency of C++ classes.

It is useful to check the presence of circular dependencies.

## Installation

The script depends on [Graphviz](https://www.graphviz.org/) to draw the graph. 

On Ubuntu, you can install the dependencies with these two commands:

```
brew install graphviz
pip3 install -r requirements.txt
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

## Examples

Example of a graph produced by the script:

./dependency_graph.py "$folder" --output "$(basename $folder)"
output files:
* nodes.txt
* edges.txt
* graph.jpg
* graph.pdf

![Example 2](https://github.com/pvigier/dependency-graph/raw/master/examples/example2.png)
