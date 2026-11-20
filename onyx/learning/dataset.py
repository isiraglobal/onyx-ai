"""Dataset synthesis, schema formatting, and validation."""

from dataclasses import dataclass, asdict
import json
from pathlib import Path
import random
import time
from typing import Dict, List, Optional, Any, Tuple


@dataclass
class TrainingExample:
    instruction: str
    output: str
    input: str = ""
    source: str = "curated"
    quality_score: float = 1.0

    def to_alpaca(self) -> Dict[str, Any]:
        return {
            "instruction": self.instruction,
            "input": self.input,
            "output": self.output,
        }

    def to_sharegpt(self) -> Dict[str, Any]:
        conversations = []
        if self.input:
            conversations.append({"from": "human", "value": f"{self.instruction}\n\nContext:\n{self.input}"})
        else:
            conversations.append({"from": "human", "value": self.instruction})
        conversations.append({"from": "gpt", "value": self.output})
        return {"conversations": conversations}

    def to_chatml(self) -> Dict[str, Any]:
        messages = []
        user_content = f"{self.instruction}\n\nContext:\n{self.input}" if self.input else self.instruction
        messages.append({"role": "user", "content": user_content})
        messages.append({"role": "assistant", "content": self.output})
        return {"messages": messages}


class DatasetBuilder:
    """Constructs, validates, and splits training datasets from documents and conversations."""

    def __init__(self, output_dir: str = "data/learning/datasets"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def validate_example(self, example: TrainingExample) -> Tuple[bool, Optional[str]]:
        """Validate an individual training pair."""
        if not example.instruction or len(example.instruction.strip()) < 5:
            return False, "Instruction too short (< 5 chars)"
        if not example.output or len(example.output.strip()) < 5:
            return False, "Output too short (< 5 chars)"
        if len(example.instruction) > 16000:
            return False, "Instruction exceeds maximum length (16k chars)"
        return True, None

    def create_dataset(
        self,
        name: str,
        examples: List[TrainingExample],
        format_type: str = "chatml",  # chatml | alpaca | sharegpt
        val_split: float = 0.15,
    ) -> Dict[str, Any]:
        """Validate, split, and save dataset to disk."""
        valid_examples = []
        rejections = []

        for ex in examples:
            is_valid, reason = self.validate_example(ex)
            if is_valid:
                valid_examples.append(ex)
            else:
                rejections.append({"example": asdict(ex), "reason": reason})

        if not valid_examples:
            raise ValueError(f"No valid examples found in dataset. Rejections: {len(rejections)}")

        # Shuffle and split
        shuffled = list(valid_examples)
        random.seed(42)
        random.shuffle(shuffled)

        split_idx = int(len(shuffled) * (1.0 - val_split))
        train_set = shuffled[:split_idx]
        val_set = shuffled[split_idx:] if val_split > 0 else []

        ds_dir = self.output_dir / name
        ds_dir.mkdir(parents=True, exist_ok=True)

        train_file = ds_dir / "train.jsonl"
        val_file = ds_dir / "val.jsonl"

        def _format(ex: TrainingExample) -> Dict[str, Any]:
            if format_type == "alpaca":
                return ex.to_alpaca()
            elif format_type == "sharegpt":
                return ex.to_sharegpt()
            return ex.to_chatml()

        with open(train_file, "w", encoding="utf-8") as f:
            for ex in train_set:
                f.write(json.dumps(_format(ex)) + "\n")

        with open(val_file, "w", encoding="utf-8") as f:
            for ex in val_set:
                f.write(json.dumps(_format(ex)) + "\n")

        meta = {
            "name": name,
            "created_at": time.time(),
            "format": format_type,
            "total_examples": len(valid_examples),
            "train_count": len(train_set),
            "val_count": len(val_set),
            "rejected_count": len(rejections),
            "train_file": str(train_file),
            "val_file": str(val_file),
        }
        (ds_dir / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

        return meta
