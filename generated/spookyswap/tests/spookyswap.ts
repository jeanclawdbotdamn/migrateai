import * as anchor from "@coral-xyz/anchor";
import { Program } from "@coral-xyz/anchor";
import { Spookyswap } from "../target/types/spookyswap";
import { expect } from "chai";

describe("spookyswap", () => {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  const program = anchor.workspace.Spookyswap as Program<Spookyswap>;

  it("Initializes successfully", async () => {
    // TODO: Add initialization test
    console.log("Program ID:", program.programId.toString());
  });

  // TODO: Add tests for each migrated contract function
  // Tip: Use anchor.web3.Keypair.generate() for test accounts
  // Tip: Use getAssociatedTokenAddress() for token accounts
});
