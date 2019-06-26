# VeriBlock Stratum Reference Implementation

This reference implementation is derived from slush0's original Stratum work. The original project can be found here:
* https://github.com/slush0/stratum
* https://github.com/slush0/stratum-mining

Modification was made to the stratum project to use Python 3.7, and the stratum-mining project customized to proxy VeriBlock NodeCore's UCP protocol and support the VeriBlock header format and hashing algorithm.

Included in this repository are the Stratum framework, custom VeriBlock Stratum implementation and a reference CPU miner.

## Build - Stratum Server
The Stratum server components are written in Python.

By convention, all references to `{ROOT}` below represent the root folder of the repository.

### Prerequisites
* Python 3.7
* pip
* virtualenv (Recommended)

### Build Steps
1. (Optional) Create and activate a virtual environment
```
$ cd {ROOT}\stratum-server
$ virtualenv -p "C:\Python37\python.exe" venv
$ venv\Scripts\activate
```

2. Install required packages
```
$ pip install -r requirements.txt
```

3. Install Stratum framework package (from source)
```
$ cd {ROOT}\stratum-server\stratum
$ python setup.py install
```
	
4. Install vBlake package (from source)
```
$ cd {ROOT}\stratum-server\vblake
$ python setup.py install
```

## Build - Reference PoW Miner
The reference PoW miner is written in Java.

1. Build with gradlew
```
$ cd {ROOT}\reference-miner
$ gradlew clean installDist
```

The executable script will be found at `{ROOT}\reference-miner\build\install\nodecore-pow\bin`

## Run

1. Start NodeCore. NodeCore should be built and run from the source code feature branch `feature/stratum`
2. Start a **SOLO** mining pool on NodeCore, by issuing the RPC command `startsolopool` via CLI or HTTP API.
3. Run the Stratum server instance
```
	$ cd {ROOT}\stratum-server
	$ twistd -ny launcher.tac
```
4. Run the reference PoW miner. The Stratum server will be running at `127.0.0.1:3333` and should be the value used to connect to in the miner.