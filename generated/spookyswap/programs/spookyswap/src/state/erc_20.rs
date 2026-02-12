use anchor_lang::prelude::*;

/// Token configuration (replaces ERC-20 contract state)
/// EVM: name, symbol, decimals, totalSupply stored in contract
/// Solana: Stored in a PDA account
#[account]
#[derive(InitSpace)]
pub struct TokenConfig {
    pub authority: Pubkey,      // EVM: owner()
    pub mint: Pubkey,           // The SPL token mint
    #[max_len(32)]
    pub name: String,           // EVM: name()
    #[max_len(8)]
    pub symbol: String,         // EVM: symbol()
    pub decimals: u8,           // EVM: decimals()
    pub total_supply: u64,      // EVM: totalSupply()
}

// EVM events → Anchor events
#[event]
pub struct TokensMinted {
    pub to: Pubkey,
    pub amount: u64,
}
