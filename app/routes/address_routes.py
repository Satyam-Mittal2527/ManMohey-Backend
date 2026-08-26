from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user

from app.schemas.address import (
    AddressCreate,
    AddressUpdate,
)

from app.services.address_service import (
    get_user_addresses,
    get_address_by_id,
    create_address,
    update_address,
    delete_address,
    set_default_address,
)


router = APIRouter(prefix="/api/addresses")


@router.get("/")
async def getAddresses(
    current_user=Depends(get_current_user)
):

    return get_user_addresses(
        current_user["user_id"]
    )


@router.get("/{address_id}")
async def getAddress(
    address_id: str,
    current_user=Depends(get_current_user)
):

    return get_address_by_id(
        current_user["user_id"],
        address_id
    )


@router.post("/add")
async def addAddress(
    payload: AddressCreate,
    current_user=Depends(get_current_user)
):

    print(
        "Received request to add address:",
        payload
    )

    return create_address(
        current_user["user_id"],
        payload
    )


@router.put("/{address_id}")
async def updateAddress(
    address_id: str,
    payload: AddressUpdate,
    current_user=Depends(get_current_user)
):

    print(
        f"Updating address: {address_id}"
    )

    return update_address(
        current_user["user_id"],
        address_id,
        payload
    )


@router.delete("/{address_id}")
async def deleteAddress(
    address_id: str,
    current_user=Depends(get_current_user)
):

    print(
        f"Deleting address: {address_id}"
    )

    return delete_address(
        current_user["user_id"],
        address_id
    )


@router.put("/{address_id}/default")
async def setDefaultAddress(
    address_id: str,
    current_user=Depends(get_current_user)
):

    print(
        f"Setting default address: {address_id}"
    )

    return set_default_address(
        current_user["user_id"],
        address_id
    )