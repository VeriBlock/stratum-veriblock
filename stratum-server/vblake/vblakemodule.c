#include <Python.h>
#include "vblake.h"

static PyObject *vblake_getpowhash(PyObject *self, PyObject *args, PyObject* kwargs) {
    char *input;
    int      inputlen;

    char *outbuf;
    size_t outbuflen;

    static char *g2_kwlist[] = {"input", NULL};

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "y#", g2_kwlist,
                                     &input, &inputlen)) {
        return NULL;
    }

    outbuf = PyMem_Malloc(24);
    outbuflen = 24;

    Py_BEGIN_ALLOW_THREADS;
    
    hash(input, outbuf);

    Py_END_ALLOW_THREADS;
    
    PyObject *value = NULL;
    value = Py_BuildValue("y#", outbuf, 24);
    
    PyMem_Free(outbuf);
    return value;
}


static PyMethodDef VBlakeMethods[] = {
    { "getPoWHash", (PyCFunction) vblake_getpowhash, METH_VARARGS | METH_KEYWORDS, "Returns the proof of work hash using vBlake" },
    { NULL, NULL, 0, NULL }
};

static struct PyModuleDef vblakemodule = {
    PyModuleDef_HEAD_INIT,
    "vblake",
    NULL,
    -1,
    VBlakeMethods
};

PyMODINIT_FUNC PyInit_vblake(void) {
    PyObject *m = PyModule_Create(&vblakemodule);

    if (m == NULL) {
        return NULL;
    }

    return m;
}