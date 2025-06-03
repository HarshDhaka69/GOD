from . import db

# Use a single collection for both ads and shortner since they're the same feature
db = db.ads_shortner

async def enable_feature() -> None:
    """Enable ads/shortner functionality"""
    await db.delete_one({'enabled': False})

async def disable_feature() -> None:
    """Disable ads/shortner functionality"""
    await db.insert_one({'enabled': False})

async def is_disabled() -> bool:
    """Check if ads/shortner is disabled"""
    return bool(await db.find_one({'enabled': False}))

# Alias functions for backward compatibility
enable_ads = enable_shortner = enable_feature
disable_ads = disable_shortner = disable_feature
is_ad_disabled = is_shortner_disabled = is_disabled 