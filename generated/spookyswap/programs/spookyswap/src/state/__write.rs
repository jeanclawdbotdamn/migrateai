use anchor_lang::prelude::*;

/// --write state — customize for your migration
#[account]
#[derive(InitSpace)]
pub struct writeState {
    pub authority: Pubkey,
    pub initialized: bool,
    pub bump: u8,
}
