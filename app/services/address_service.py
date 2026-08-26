from fastapi import HTTPException

from app.db.supabase_client import supabase_admin


def get_user_addresses(user_id: str):

    try:
        response = (
            supabase_admin
            .table("addresses")
            .select("*")
            .eq("user_id", user_id)
            .order("is_default", desc=True)
            .order("created_at", desc=True)
            .execute()
        )

        return response.data or []

    except Exception as e:
        print(f"Get user addresses error: {e}")
        raise


def get_address_by_id(
    user_id: str,
    address_id: str,
):

    try:
        response = (
            supabase_admin
            .table("addresses")
            .select("*")
            .eq("id", address_id)
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=404,
                detail="Address not found",
            )

        return response.data

    except HTTPException:
        raise

    except Exception as e:
        print(f"Get address error: {e}")
        raise


def create_address(
    user_id: str,
    address_data,
):

    try:

        data = address_data.model_dump()

        # If this address is default,
        # remove default status from existing addresses.
        if data.get("is_default"):

            (
                supabase_admin
                .table("addresses")
                .update({
                    "is_default": False
                })
                .eq("user_id", user_id)
                .execute()
            )

        data["user_id"] = user_id

        response = (
            supabase_admin
            .table("addresses")
            .insert(data)
            .execute()
        )

        if not response.data:
            raise Exception(
                "Failed to create address"
            )

        return response.data[0]

    except Exception as e:
        print(f"Create address error: {e}")
        raise


def update_address(
    user_id: str,
    address_id: str,
    address_data,
):

    try:

        # First make sure the address belongs
        # to the authenticated user.
        existing = get_address_by_id(
            user_id,
            address_id,
        )

        data = address_data.model_dump(
            exclude_unset=True
        )

        if not data:
            return existing

        # If making this address default,
        # remove default from all other addresses.
        if data.get("is_default") is True:

            (
                supabase_admin
                .table("addresses")
                .update({
                    "is_default": False
                })
                .eq("user_id", user_id)
                .neq("id", address_id)
                .execute()
            )

        response = (
            supabase_admin
            .table("addresses")
            .update(data)
            .eq("id", address_id)
            .eq("user_id", user_id)
            .execute()
        )

        if not response.data:
            raise Exception(
                "Failed to update address"
            )

        return response.data[0]

    except HTTPException:
        raise

    except Exception as e:
        print(f"Update address error: {e}")
        raise


def delete_address(
    user_id: str,
    address_id: str,
):

    try:

        # Verify ownership first.
        get_address_by_id(
            user_id,
            address_id,
        )

        response = (
            supabase_admin
            .table("addresses")
            .delete()
            .eq("id", address_id)
            .eq("user_id", user_id)
            .execute()
        )

        return {
            "message": "Address deleted successfully"
        }

    except HTTPException:
        raise

    except Exception as e:
        print(f"Delete address error: {e}")
        raise


def set_default_address(
    user_id: str,
    address_id: str,
):

    try:

        # Verify ownership.
        get_address_by_id(
            user_id,
            address_id,
        )

        # Remove default from all user's addresses.
        (
            supabase_admin
            .table("addresses")
            .update({
                "is_default": False
            })
            .eq("user_id", user_id)
            .execute()
        )

        # Set selected address as default.
        response = (
            supabase_admin
            .table("addresses")
            .update({
                "is_default": True
            })
            .eq("id", address_id)
            .eq("user_id", user_id)
            .execute()
        )

        if not response.data:
            raise Exception(
                "Failed to set default address"
            )

        return response.data[0]

    except HTTPException:
        raise

    except Exception as e:
        print(
            f"Set default address error: {e}"
        )
        raise