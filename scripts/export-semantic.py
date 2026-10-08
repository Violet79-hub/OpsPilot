"""Export pinned Apache-2.0 static retrieval weights for API-free Worker inference.
Usage: python scripts/export-semantic.py /directory/with/downloaded/model/files
The first 128 Matryoshka dimensions are quantized per token to signed int8.
"""
import base64,hashlib,json,struct,sys
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1];source=Path(sys.argv[1]);raw=(source/'model.safetensors').read_bytes();n=struct.unpack('<Q',raw[:8])[0];header=json.loads(raw[8:8+n]);meta=header['embedding.weight'];assert meta['dtype']=='F32'
w=np.frombuffer(raw,dtype='<f4',offset=8+n).reshape(meta['shape'])[:,:128].copy();scale=np.maximum(np.abs(w).max(axis=1)/127,1e-12);q=np.rint(w/scale[:,None]).clip(-127,127).astype('int8')
t=json.loads((source/'tokenizer.json').read_text());vocab=t['model']['vocab'];dest=root/'lib/agent/semantic-artifact.json';dest.write_text(json.dumps({'model':'sentence-transformers/static-retrieval-mrl-en-v1','revision':'f60985c706f192d45d218078e49e5a8b6f15283a','license':'Apache-2.0','dimensions':128,'source_dimensions':1024,'source_sha256':hashlib.sha256(raw).hexdigest(),'quantization':'per-token symmetric int8','vocab':vocab,'scales':scale.tolist(),'weights':base64.b64encode(q.tobytes()).decode()},separators=(',',':')))
# Fixed token sequences test independent NumPy quantized mean + normalization.
cases=[]
for words in [['money','back'],['cancel','my','subscription'],['personal','information'],['credit','report'],['bank','account']]:
 ids=[vocab[x] for x in words];vec=(q[ids].astype(np.float32)*scale[ids,None]).mean(axis=0);vec/=np.linalg.norm(vec);original=w[ids].mean(axis=0);original/=np.linalg.norm(original);cases.append({'text':' '.join(words),'tokens':ids,'vector':vec.tolist(),'float_cosine':float(vec@original)})
(root/'verification/semantic-parity.json').write_text(json.dumps(cases));print('Exported',dest.stat().st_size,'bytes; min quantization cosine',min(c['float_cosine'] for c in cases))
