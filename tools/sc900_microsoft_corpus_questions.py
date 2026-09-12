from __future__ import annotations

from tools.sc900_microsoft_corpus_qemit import redistribute_single_select, write_batch, write_reviews
from tools.sc900_mlc_batch01 import batch_01
from tools.sc900_mlc_batch02 import batch_02
from tools.sc900_mlc_batch03 import batch_03
from tools.sc900_mlc_batch04 import batch_04
from tools.sc900_mlc_batch05 import batch_05
from tools.sc900_mlc_batch06 import batch_06
from tools.sc900_mlc_batch07 import batch_07
from tools.sc900_mlc_batch08 import batch_08
from tools.sc900_mlc_batch09 import batch_09
from tools.sc900_mlc_batch10 import batch_10
from tools.sc900_mlc_batch11 import batch_11
from tools.sc900_mlc_batch12 import batch_12

BATCHES = (
    ("batch-01", batch_01),
    ("batch-02", batch_02),
    ("batch-03", batch_03),
    ("batch-04", batch_04),
    ("batch-05", batch_05),
    ("batch-06", batch_06),
    ("batch-07", batch_07),
    ("batch-08", batch_08),
    ("batch-09", batch_09),
    ("batch-10", batch_10),
    ("batch-11", batch_11),
    ("batch-12", batch_12),
)


def write_all() -> None:
    total = 0
    for batch_id, factory in BATCHES:
        records = redistribute_single_select(factory())
        if len(records) != 25:
            raise ValueError(f"{batch_id} has {len(records)} records")
        write_batch(batch_id, records)
        write_reviews(batch_id, records)
        total += len(records)
        print(f"wrote {batch_id} count={len(records)}")
    print(f"total {total}")


if __name__ == "__main__":
    write_all()
